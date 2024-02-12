import os
import numpy as np
from puzzle import Puzzle, PuzzleParser
from argparse import ArgumentParser
from online import fetch, submit, hall
import gurobipy as gp
from gurobipy import GRB

class Sudoku(Puzzle):
    def __init__(self, input, name='Sudoku', check=False, solve=True, strategy='default', debug=False):
        super().__init__(input, name, check, solve, strategy, debug)
    
    def init_board(self):
        self.ans = self.model.addVars(self.n, self.n, vtype=GRB.INTEGER, lb=1, ub=self.n, name='ans')

    def parse_nums(self, nums):
        if len(nums) == 36:
            self.n = 6
        elif len(nums) == 81:
            self.n = 9
        elif len(nums) == 144:
            self.n = 12
        elif len(nums) == 256:
            self.n = 16
        else:
            raise ValueError(f'Invalid number of entries, got {len(nums)}')
        self.board = np.zeros((self.n, self.n), dtype=int)
        for i in range(self.n):
            for j in range(self.n):
                self.board[i, j] = nums[i*self.n+j]
        return self.board

    def parse_from_task(self, task):
        nums = []
        while task:
            if len(task) >= 2 and task[:2].isdigit():
                nums.append(int(task[:2]))
                task = task[2:]
            elif task[0].isdigit():
                nums.append(int(task[0]))
                task = task[1:]
            elif task[0].isalpha():
                cnt = ord(task[0]) - ord('a') + 1
                nums += [0] * cnt
                task = task[1:]
            elif task[0] == '_':
                task = task[1:]
            else:
                raise ValueError(f"Invalid character '{task[0]}'")
        return self.parse_nums(nums)
    
    def parse_from_file(self, file):
        with open(file, 'r') as f:
            raw = f.read()
        nums = [x for x in raw if not x.isspace()]
        nums = [int(x) if x.isdigit() else ord(x) - ord('A') + 10 if x.isalpha() else 0 for x in nums]
        return self.parse_nums(nums)
    
    def xy(self):
        if self.n == 6:
            x = 3
            y = 2
        elif self.n == 9:
            x = 3
            y = 3
        elif self.n == 12:
            x = 4
            y = 3
        elif self.n == 16:
            x = 4
            y = 4
        return x, y

    def strategy_inequality(self):
        self.model.addConstrs(self.ans[i, j] == self.board[i, j] for i in range(self.n) for j in range(self.n) if self.board[i, j] != 0)
        self.b = {}
        for i in range(self.n):
            for j in range(self.n):
                for k in range(j+1, self.n):
                    self.b[i, j, i, k] = self.model.addVar(vtype=GRB.BINARY, name=f'b_{i}_{j}_{i}_{k}')
                    self.b[j, i, k, i] = self.model.addVar(vtype=GRB.BINARY, name=f'b_{j}_{i}_{k}_{i}')
                    self.model.addConstr((self.b[i, j, i, k] == 0) >> (self.ans[i, j] <= self.ans[i, k] - 1))
                    self.model.addConstr((self.b[i, j, i, k] == 1) >> (self.ans[i, j] >= self.ans[i, k] + 1))
                    self.model.addConstr((self.b[j, i, k, i] == 0) >> (self.ans[j, i] <= self.ans[k, i] - 1))
                    self.model.addConstr((self.b[j, i, k, i] == 1) >> (self.ans[j, i] >= self.ans[k, i] + 1))
        x, y = self.xy()
        for i in range(x):
            for j in range(y):
                pairs = [(i*y+k, j*x+l) for k in range(y) for l in range(x)]
                for k in range(len(pairs)):
                    for l in range(k+1, len(pairs)):
                        x1, y1 = pairs[k]
                        x2, y2 = pairs[l]
                        if not (x1, y1, x2, y2) in self.b:
                            self.b[x1, y1, x2, y2] = self.model.addVar(vtype=GRB.BINARY, name=f'b_{x1}_{y1}_{x2}_{y2}')
                            self.model.addConstr((self.b[x1, y1, x2, y2] == 0) >> (self.ans[x1, y1] <= self.ans[x2, y2] - 1))
                            self.model.addConstr((self.b[x1, y1, x2, y2] == 1) >> (self.ans[x1, y1] >= self.ans[x2, y2] + 1))
    
    def strategy_default(self):
        self.model.addConstrs(self.ans[i, j] == self.board[i, j] for i in range(self.n) for j in range(self.n) if self.board[i, j] != 0)
        self.b = self.model.addVars(self.n, self.n, range(1, self.n+1), vtype=GRB.BINARY, name='b')
        for i in range(self.n):
            for j in range(self.n):
                self.model.addConstr(gp.quicksum(self.b[i, j, k] for k in range(1, self.n+1)) == 1)
                for k in range(1, self.n+1):
                    self.model.addConstr((self.b[i, j, k] == 1) >> (self.ans[i, j] == k))
        for i in range(self.n):
            for k in range(1, self.n+1):
                self.model.addConstr(gp.quicksum(self.b[i, j, k] for j in range(self.n)) == 1)
                self.model.addConstr(gp.quicksum(self.b[j, i, k] for j in range(self.n)) == 1)
        x, y = self.xy()
        for i in range(x):
            for j in range(y):
                pairs = [(i*y+k, j*x+l) for k in range(y) for l in range(x)]
                for k in range(1, self.n+1):
                    self.model.addConstr(gp.quicksum(self.b[p[0], p[1], k] for p in pairs) == 1)

    def strategy_bank(self):
        return {'default': self.strategy_default, 'inequality': self.strategy_inequality}
    
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
            res = ''
            for i in range(self.n):
                for j in range(self.n):
                    res += str(round(self.ans[i, j].X)) + ' '
                res += '\n'
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

class Diagonal(Sudoku):
    def __init__(self, file, name='Diagonal Sudoku', check=False, solve=True, strategy='default', debug=False):
        super().__init__(file, name, check, solve, strategy, debug)

    def strategy_default(self):
        super().strategy_default()
        for k in range(1, self.n+1):
            self.model.addConstr(gp.quicksum(self.b[i, i, k] for i in range(self.n)) == 1)
            self.model.addConstr(gp.quicksum(self.b[i, self.n-i-1, k] for i in range(self.n)) == 1)

    def strategy_bank(self):
        return {'default': self.strategy_default}

class SudokuParser(PuzzleParser):
    def __init__(self, description='Sudoku Solver'):
        super().__init__(description)
    
    def init_config(self):
        return {'normal': {'class': Sudoku, 'file': 'example/sudoku.txt'},
                'diagonal': {'class': Diagonal, 'file': 'example/diagonal.txt'}}
    
    def add_extra_args(self):
        '''
        0: 3x3 Basic Sudoku
        1: 3x3 Easy Sudoku
        2: 3x3 Intermediate Sudoku
        3: 3x3 Advanced Sudoku
        4: 3x3 Extreme Sudoku
        5: 3x3 Evil Sudoku
        6: 3x4 Sudoku
        7: 4x4 Sudoku
        8: Daily Sandwich Sudoku
        9: Special Daily Sudoku
        10: Special Weekly Sudoku
        11: Special Monthly Sudoku
        '''
        self.add_argument('--domain', type=str, default='puzzle-sudoku', help='Domain of the online puzzle')
        self.add_argument('--diff', type=int, default=0, help='Difficulty of the online puzzle', choices=range(12))


if __name__ == '__main__':
    parser = SudokuParser()
    parser.main()