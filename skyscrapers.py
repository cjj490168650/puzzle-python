import os
import argparse
import numpy as np
from online import fetch, submit, hall
from docplex.mp.model import Model

class Skyscrapers():
    def __init__(self, file, name='Skyscrapers', check=False, solve=True):
        self.name = name
        self.file = file
        self.n = 0
        self.board = self.read(file)
        self.model = Model(name)
        self.model.output_level = "error"
        self.ans = self.model.integer_var_matrix(self.n, self.n, 1, self.n, 'ans')
        if solve:
            self.ans = self.solve()
        self.check = check
        if solve and check:
            try:
                self.unique = self.check_unique()
            except Exception as e:
                self.unique = f'Error: {e}'
    
    def parse(self, task):
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
        return res

    def read(self, file):
        if os.path.exists(file):
            with open(file, 'r') as f:
                raw = f.read()
        else:
            raw = self.parse(file)
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
    
    def add_constraints(self):
        for i in range(self.n):
            for j in range(self.n):
                if self.board['b'][i, j]:
                    self.model.add_constraint(self.ans[i, j] == self.board['b'][i, j])
        for i in range(self.n):
            for j in range(self.n):
                for k in range(j+1, self.n):
                    self.model.add_constraint(self.ans[i, j] != self.ans[i, k])
                    self.model.add_constraint(self.ans[j, i] != self.ans[k, i])
        self.cmp = self.model.binary_var_dict([(i, j, x, y) for i in range(self.n) for j in range(self.n) for x in range(self.n) for y in range(self.n) 
                                               if (i == x and j != y) or (i != x and j == y)], name='cmp')
        for i in range(self.n):
            for j in range(self.n):
                for x in range(self.n):
                    for y in range(self.n):
                        if (i == x and j != y) or (i != x and j == y):
                            self.model.add_indicator(self.cmp[i, j, x, y], self.ans[i, j] >= self.ans[x, y]+1, active_value=1)
                            self.model.add_indicator(self.cmp[i, j, x, y], self.ans[i, j] <= self.ans[x, y]-1, active_value=0)
        self.visible = self.model.binary_var_dict([(i, j, d) for i in range(self.n) for j in range(self.n) for d in ['u', 'd', 'l', 'r']], name='visible')
        for i in range(self.n):
            for j in range(self.n):
                self.model.add_indicator(self.visible[i, j, 'u'], self.model.sum(self.cmp[i, j, k, j] for k in range(i)) == i, active_value=1)
                self.model.add_indicator(self.visible[i, j, 'u'], self.model.sum(self.cmp[i, j, k, j] for k in range(i)) <= i-1, active_value=0)
                self.model.add_indicator(self.visible[i, j, 'd'], self.model.sum(self.cmp[i, j, k, j] for k in range(i+1, self.n)) == self.n-i-1, active_value=1)
                self.model.add_indicator(self.visible[i, j, 'd'], self.model.sum(self.cmp[i, j, k, j] for k in range(i+1, self.n)) <= self.n-i-2, active_value=0)
                self.model.add_indicator(self.visible[i, j, 'l'], self.model.sum(self.cmp[i, j, i, k] for k in range(j)) == j, active_value=1)
                self.model.add_indicator(self.visible[i, j, 'l'], self.model.sum(self.cmp[i, j, i, k] for k in range(j)) <= j-1, active_value=0)
                self.model.add_indicator(self.visible[i, j, 'r'], self.model.sum(self.cmp[i, j, i, k] for k in range(j+1, self.n)) == self.n-j-1, active_value=1)
                self.model.add_indicator(self.visible[i, j, 'r'], self.model.sum(self.cmp[i, j, i, k] for k in range(j+1, self.n)) <= self.n-j-2, active_value=0)
        for i in range(self.n):
            if self.board['u'][i]:
                self.model.add_constraint(self.model.sum(self.visible[j, i, 'u'] for j in range(self.n)) == self.board['u'][i])
            if self.board['d'][i]:
                self.model.add_constraint(self.model.sum(self.visible[j, i, 'd'] for j in range(self.n)) == self.board['d'][i])
            if self.board['l'][i]:
                self.model.add_constraint(self.model.sum(self.visible[i, j, 'l'] for j in range(self.n)) == self.board['l'][i])
            if self.board['r'][i]:
                self.model.add_constraint(self.model.sum(self.visible[i, j, 'r'] for j in range(self.n)) == self.board['r'][i])

    def solve(self):
        self.add_constraints()
        self.model.solve()
        return self.ans
    
    def check_unique(self):
        clone = self.__class__(self.file, name=self.name + ' Clone', solve=False)
        clone.flag = clone.model.binary_var_matrix(self.n, self.n, 'flag')
        for i in range(self.n):
            for j in range(self.n):
                clone.model.add_indicator(clone.flag[i, j], clone.ans[i, j] != round(self.ans[i, j].solution_value))
        clone.model.add_constraint(clone.model.sum(clone.flag) >= 1)
        clone.ans = clone.solve()
        result = clone.pretty()
        if 'did not solve successfully' in result:
            return 'The solution is unique'
        elif 'Error' in result:
            return f'Error: {result}'
        else:
            return 'The solution is not unique\n' + result
    
    def pretty(self):
        try:
            res = '  '
            res += ' '.join(str(x) if x else '*' for x in self.board['u'])
            res += '\n'
            for i in range(self.n):
                res += str(self.board['l'][i]) if self.board['l'][i] else '*'
                res += ' '
                for j in range(self.n):
                    t = round(self.ans[i, j].solution_value)
                    res += str(t) + ' '
                res += str(self.board['r'][i]) if self.board['r'][i] else '*'
                res += '\n'
            res += '  '
            res += ' '.join(str(x) if x else '*' for x in self.board['d'] )
            if self.check:
                res += '\n' + self.unique
            return res
        except Exception as e:
            return f'Error: {e}'
        
    def __str__(self):
        try:
            res = ''
            for i in range(self.n):
                for j in range(self.n):
                    res += str(round(self.ans[i, j].solution_value)) + ','
            return res
        except Exception as e:
            return f'Error: {e}'
    
class Color(Skyscrapers):
    '''
    https://puzzle.university/puzzle/classical-influences-on-modern-architecture.html
    '''
    def __init__(self, file, name='Color Skyscrapers', check=False, solve=True):
        super().__init__(file, name, check, solve=False)
        self.colors = ['R', 'O', 'Y', 'G', 'B', 'P', 'V']
        self.color = self.model.integer_var_dict(self.colors, lb=1, ub=self.n, name='color')
        if solve:
            self.ans = self.solve()
        if solve and check:
            try:
                self.unique = self.check_unique()
            except Exception as e:
                self.unique = f'Error: {e}'
    
    def read(self, file):
        with open(file, 'r') as f:
            raw = f.read()
        lines = raw.split('\n')
        lines = [line.strip().replace(' ', '').replace('\t', '') for line in lines if line.strip()]
        self.board = {}
        for line in lines:
            d = line[0].lower()
            nums = [x for x in line if x.isupper()]
            self.board[d] = nums
        self.n = len(self.board['u'])
        return self.board
    
    def add_constraints(self):
        for i in range(len(self.colors)):
            for j in range(i+1, len(self.colors)):
                self.model.add_constraint(self.color[self.colors[i]] != self.color[self.colors[j]])
        for i in range(self.n):
            for j in range(self.n):
                for k in range(j+1, self.n):
                    self.model.add_constraint(self.ans[i, j] != self.ans[i, k])
                    self.model.add_constraint(self.ans[j, i] != self.ans[k, i])
        self.cmp = self.model.binary_var_dict([(i, j, x, y) for i in range(self.n) for j in range(self.n) for x in range(self.n) for y in range(self.n) 
                                               if (i == x and j != y) or (i != x and j == y)], name='cmp')
        for i in range(self.n):
            for j in range(self.n):
                for x in range(self.n):
                    for y in range(self.n):
                        if (i == x and j != y) or (i != x and j == y):
                            self.model.add_indicator(self.cmp[i, j, x, y], self.ans[i, j] >= self.ans[x, y]+1, active_value=1)
                            self.model.add_indicator(self.cmp[i, j, x, y], self.ans[i, j] <= self.ans[x, y]-1, active_value=0)
        self.visible = self.model.binary_var_dict([(i, j, d) for i in range(self.n) for j in range(self.n) for d in ['u', 'd', 'l', 'r']], name='visible')
        for i in range(self.n):
            for j in range(self.n):
                self.model.add_indicator(self.visible[i, j, 'u'], self.model.sum(self.cmp[i, j, k, j] for k in range(i)) == i, active_value=1)
                self.model.add_indicator(self.visible[i, j, 'u'], self.model.sum(self.cmp[i, j, k, j] for k in range(i)) <= i-1, active_value=0)
                self.model.add_indicator(self.visible[i, j, 'd'], self.model.sum(self.cmp[i, j, k, j] for k in range(i+1, self.n)) == self.n-i-1, active_value=1)
                self.model.add_indicator(self.visible[i, j, 'd'], self.model.sum(self.cmp[i, j, k, j] for k in range(i+1, self.n)) <= self.n-i-2, active_value=0)
                self.model.add_indicator(self.visible[i, j, 'l'], self.model.sum(self.cmp[i, j, i, k] for k in range(j)) == j, active_value=1)
                self.model.add_indicator(self.visible[i, j, 'l'], self.model.sum(self.cmp[i, j, i, k] for k in range(j)) <= j-1, active_value=0)
                self.model.add_indicator(self.visible[i, j, 'r'], self.model.sum(self.cmp[i, j, i, k] for k in range(j+1, self.n)) == self.n-j-1, active_value=1)
                self.model.add_indicator(self.visible[i, j, 'r'], self.model.sum(self.cmp[i, j, i, k] for k in range(j+1, self.n)) <= self.n-j-2, active_value=0)
        for i in range(self.n):
            self.model.add_constraint(self.model.sum(self.visible[j, i, 'u'] for j in range(self.n)) == self.color[self.board['u'][i]])
            self.model.add_constraint(self.model.sum(self.visible[j, i, 'd'] for j in range(self.n)) == self.color[self.board['d'][i]])
            self.model.add_constraint(self.model.sum(self.visible[i, j, 'l'] for j in range(self.n)) == self.color[self.board['l'][i]])
            self.model.add_constraint(self.model.sum(self.visible[i, j, 'r'] for j in range(self.n)) == self.color[self.board['r'][i]])

    def pretty(self):
        try:
            res = '  '
            res += ' '.join(str(round(self.color[x].solution_value)) for x in self.board['u'])
            res += '\n'
            for i in range(self.n):
                res += str(round(self.color[self.board['l'][i]].solution_value))
                res += ' '
                for j in range(self.n):
                    t = round(self.ans[i, j].solution_value)
                    res += str(t) + ' '
                res += str(round(self.color[self.board['r'][i]].solution_value))
                res += '\n'
            res += '  '
            res += ' '.join(str(round(self.color[x].solution_value)) for x in self.board['d'] )
            if self.check:
                res += '\n' + self.unique
            return res
        except Exception as e:
            return f'Error: {e}'
        

if __name__ == '__main__':

    config = {
        'normal': {'class': Skyscrapers, 'file': 'example/skyscrapers.txt'},
        'color': {'class': Color, 'file': 'example/colorskyscrapers.txt'}
    }

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', type=str, help='File containing the puzzle')
    parser.add_argument('-o', '--output', type=str, help='File to save the solution')
    parser.add_argument('--check', default=False, action='store_true', help='Check if the solution is unique')
    parser.add_argument('--type', type=str, default='normal', help='Type of puzzle', choices=config.keys())
    parser.add_argument('--online', default=False, action='store_true', help='Solve puzzle online')
    parser.add_argument('--diff', type=int, default=0, help='Difficulty of the online puzzle')
    parser.add_argument('-n', type=int, default=1, help='Number of puzzles to solve')

    args = parser.parse_args()
    if args.online:
        os.environ['http_proxy'] = '127.0.0.1:10809'
        os.environ['https_proxy'] = '127.0.0.1:10809'
        url = f'https://www.puzzle-skyscrapers.com/?size={args.diff}'
        for i in range(args.n):
            task, param = fetch(url)
            solver = config['normal']['class'](task, check=False)
            result = str(solver)
            response, solparam = submit(url, result, param)
            if not solparam:
                print(response)
            else:
                code = hall(url, solparam)
                if code == 200:
                    response += ' (submit to hall successfully)'
                else:
                    response += f' (Error: {code})'
                print(response)
    else:
        if not args.file:
            args.file = config[args.type]['file']
        solver = config[args.type]['class'](args.file, check=args.check)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(solver.pretty())
        else:
            print(solver.pretty())