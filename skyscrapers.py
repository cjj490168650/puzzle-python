import os
import numpy as np
from puzzle import Puzzle, PuzzleParser
from argparse import ArgumentParser
from online import fetch, submit, hall
import gurobipy as gp
from gurobipy import GRB

class Skyscrapers(Puzzle):
    def __init__(self, input, name='Skyscrapers', check=False, solve=True, strategy='default', debug=False):
        super().__init__(input, name, check, solve, strategy, debug)

    def init_board(self):
        self.ans = self.model.addVars(self.n, self.n, vtype=GRB.INTEGER, lb=1, ub=self.n, name='ans')

    def parse(self, raw):
        lines = raw.split('\n')
        lines = [line.strip().replace(' ', '').replace('\t', '') for line in lines if line.strip()]
        self.board = {}
        for line in lines[:4]:
            d = line[0].lower()
            nums = [x for x in line if not x.isalpha()]
            nums = [int(x) if x.isdigit() else 0 for x in nums]
            self.board[d] = nums
        self.n = len(self.board['u'])
        self.board['b'] = np.zeros((self.n, self.n), dtype=int)
        if len(lines) > 4:
            nums = [x for line in lines[4:] for x in line if not x.isspace()]
            if len(nums) != self.n * self.n:
                raise ValueError(f'Invalid length of board, expect {self.n*self.n}, got {len(nums)}')
            for i in range(self.n):
                for j in range(self.n):
                    if nums[i*self.n+j].isdigit():
                        self.board['b'][i, j] = int(nums[i*self.n+j])
        return self.board
        
    def parse_from_task(self, task):
        board = ''
        if ',' in task:
            task, board = task.split(',')
        nums = task.split('/')
        nums = [x if x.isdigit() else '.' for x in nums]
        if len(nums) % 4:
            raise ValueError(f'Invalid length of task: {len(nums)}')
        n = len(nums) // 4
        res = 'u' + ''.join(nums[:n]) + '\n'
        res += 'd' + ''.join(nums[n:2*n]) + '\n'
        res += 'l' + ''.join(nums[2*n:3*n]) + '\n'
        res += 'r' + ''.join(nums[3*n:]) + '\n'
        if board:
            board = board.strip().replace('_', '')
            for i in range(26):
                board = board.replace(chr(ord('a') + i), '.'*(i+1))
            res += board
        return self.parse(res)
    
    def parse_from_file(self, file):
        with open(file, 'r') as f:
            raw = f.read()
        return self.parse(raw)
    
    def strategy_common(self):
        for i in range(self.n):
            for j in range(self.n):
                if self.board['b'][i, j]:
                    self.model.addConstr(self.ans[i, j] == self.board['b'][i, j])
        self.cmp = self.model.addVars([(i, j, x, y) for i in range(self.n) for j in range(self.n) for x in range(self.n) for y in range(self.n) 
                                       if (i == x and j != y) or (i != x and j == y)], vtype=GRB.BINARY, name='cmp')
        for i in range(self.n):
            for j in range(self.n):
                for x in range(self.n):
                    for y in range(self.n):
                        if (i == x and j != y) or (i != x and j == y):
                            self.model.addConstr((self.cmp[i, j, x, y] == 1) >> (self.ans[i, j] >= self.ans[x, y]+1))
                            self.model.addConstr((self.cmp[i, j, x, y] == 0) >> (self.ans[i, j] <= self.ans[x, y]-1))
        self.visible = self.model.addVars([(i, j, d) for i in range(self.n) for j in range(self.n) for d in ['u', 'd', 'l', 'r']], vtype=GRB.BINARY, name='visible')
        for i in range(self.n):
            for j in range(self.n):
                self.model.addConstr(self.visible[i, j, 'u'] == gp.and_(self.cmp[i, j, k, j] for k in range(i)))
                self.model.addConstr(self.visible[i, j, 'd'] == gp.and_(self.cmp[i, j, k, j] for k in range(i+1, self.n)))
                self.model.addConstr(self.visible[i, j, 'l'] == gp.and_(self.cmp[i, j, i, k] for k in range(j)))
                self.model.addConstr(self.visible[i, j, 'r'] == gp.and_(self.cmp[i, j, i, k] for k in range(j+1, self.n)))
    
    def strategy_default(self):
        self.strategy_common()
        for i in range(self.n):
            if self.board['u'][i]:
                self.model.addConstr(gp.quicksum(self.visible[j, i, 'u'] for j in range(self.n)) == self.board['u'][i])
            if self.board['d'][i]:
                self.model.addConstr(gp.quicksum(self.visible[j, i, 'd'] for j in range(self.n)) == self.board['d'][i])
            if self.board['l'][i]:
                self.model.addConstr(gp.quicksum(self.visible[i, j, 'l'] for j in range(self.n)) == self.board['l'][i])
            if self.board['r'][i]:
                self.model.addConstr(gp.quicksum(self.visible[i, j, 'r'] for j in range(self.n)) == self.board['r'][i])

    def init_clone(self):
        self.clone.gr = self.clone.model.addVars(self.n, self.n, vtype=GRB.BINARY, name='flag')
        self.clone.le = self.clone.model.addVars(self.n, self.n, vtype=GRB.BINARY, name='flag')
        for i in range(self.n):
            for j in range(self.n):
                self.clone.model.addConstr(self.clone.gr[i, j] + self.clone.le[i, j] <= 1)
                self.clone.model.addConstr((self.clone.gr[i, j] == 1) >> (self.clone.ans[i, j] >= round(self.ans[i, j].X) + 1))
                self.clone.model.addConstr((self.clone.le[i, j] == 1) >> (self.clone.ans[i, j] <= round(self.ans[i, j].X) - 1))
        self.clone.model.addConstr(self.clone.gr.sum() + self.clone.le.sum() >= 1)
    
    def pretty(self):
        try:
            res = '  '
            res += ' '.join(str(x) if x else '*' for x in self.board['u'])
            res += '\n'
            for i in range(self.n):
                res += str(self.board['l'][i]) if self.board['l'][i] else '*'
                res += ' '
                for j in range(self.n):
                    t = round(self.ans[i, j].X)
                    res += str(t) + ' '
                res += str(self.board['r'][i]) if self.board['r'][i] else '*'
                res += '\n'
            res += '  '
            res += ' '.join(str(x) if x else '*' for x in self.board['d'] )
            if self.check:
                res += '\n' + self.unique
            return res
        except Exception as e:
            if self.debug:
                raise e
            return f'Error: {e}'
        
    def __str__(self):
        try:
            res = ''
            for i in range(self.n):
                for j in range(self.n):
                    res += str(round(self.ans[i, j].X)) + ','
            return res
        except Exception as e:
            if self.debug:
                raise e
            return f'Error: {e}'
    
class Color(Skyscrapers):
    '''
    https://puzzle.university/puzzle/classical-influences-on-modern-architecture.html
    '''
    def __init__(self, file, name='Color Skyscrapers', check=False, solve=True, strategy='default', debug=False):
        super().__init__(file, name, check, solve, strategy, debug)

    def init_board(self):
        super().init_board()
        self.colors = ['R', 'O', 'Y', 'G', 'B', 'P', 'V']
        self.color = self.model.addVars(self.colors, vtype=GRB.INTEGER, lb=1, ub=self.n, name='color')
    
    def parse(self, raw):
        lines = raw.split('\n')
        lines = [line.strip().replace(' ', '').replace('\t', '') for line in lines if line.strip()]
        self.board = {}
        for line in lines:
            d = line[0].lower()
            nums = [x for x in line if x.isupper()]
            self.board[d] = nums
        self.n = len(self.board['u'])
        self.board['b'] = np.zeros((self.n, self.n), dtype=int)
        return self.board
    
    def parse_from_task(self, task):
        raise NotImplementedError
    
    def strategy_default(self):
        self.strategy_common()
        self.b = self.model.addVars(self.colors, range(1, self.n+1), vtype=GRB.BINARY, name='b')
        for i in self.colors:
            self.model.addConstr(gp.quicksum(self.b[i, j] for j in range(1, self.n+1)) == 1)
            for j in range(1, self.n+1):
                self.model.addConstr((self.b[i, j] == 1) >> (self.color[i] == j))
        for j in range(1, self.n+1):
            self.model.addConstr(gp.quicksum(self.b[i, j] for i in self.colors) == 1)
        for i in range(self.n):
            self.model.addConstr(gp.quicksum(self.visible[j, i, 'u'] for j in range(self.n)) == self.color[self.board['u'][i]])
            self.model.addConstr(gp.quicksum(self.visible[j, i, 'd'] for j in range(self.n)) == self.color[self.board['d'][i]])
            self.model.addConstr(gp.quicksum(self.visible[i, j, 'l'] for j in range(self.n)) == self.color[self.board['l'][i]])
            self.model.addConstr(gp.quicksum(self.visible[i, j, 'r'] for j in range(self.n)) == self.color[self.board['r'][i]])

    def pretty(self):
        try:
            res = '  '
            res += ' '.join(str(round(self.color[x].X)) for x in self.board['u'])
            res += '\n'
            for i in range(self.n):
                res += str(round(self.color[self.board['l'][i]].X))
                res += ' '
                for j in range(self.n):
                    t = round(self.ans[i, j].X)
                    res += str(t) + ' '
                res += str(round(self.color[self.board['r'][i]].X))
                res += '\n'
            res += '  '
            res += ' '.join(str(round(self.color[x].X)) for x in self.board['d'] )
            if self.check:
                res += '\n' + self.unique
            return res
        except Exception as e:
            if self.debug:
                raise e
            return f'Error: {e}'
        
    def __str__(self):
        raise NotImplementedError
    
class SkyscrapersParser(PuzzleParser):
    def __init__(self, description='Skyscrapers Solver'):
        super().__init__(description)
    
    def init_config(self):
        return {'normal': {'class': Skyscrapers, 'file': 'example/skyscrapers.txt'},
                'color': {'class': Color, 'file': 'example/colorskyscrapers.txt'}}
    
    def add_extra_args(self):
        '''
        0: 4x4 Easy Skyscrapers
        1: 4x4 Normal Skyscrapers
        2: 4x4 Hard Skyscrapers
        3: 5x5 Easy Skyscrapers
        4: 5x5 Normal Skyscrapers
        5: 5x5 Hard Skyscrapers
        6: 6x6 Easy Skyscrapers
        7: 6x6 Normal Skyscrapers
        8: 6x6 Hard Skyscrapers
        9: Special Daily Skyscrapers
        10: Special Weekly Skyscrapers
        11: Special Monthly Skyscrapers
        '''
        self.add_argument('--domain', type=str, default='puzzle-skyscrapers', help='Domain of the online puzzle')
        self.add_argument('--diff', type=int, default=0, help='Difficulty of the online puzzle', choices=range(12))

if __name__ == '__main__':
    parser = SkyscrapersParser()
    parser.main()