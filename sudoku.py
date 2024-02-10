import os
import argparse
import numpy as np
from online import fetch, submit, hall
from docplex.mp.model import Model

class Sudoku():
    def __init__(self, file, name='Sudoku', check=False, solve=True, strategy='default'):
        self.name = name
        self.file = file
        self.n = 9
        self.board = self.read(file)
        self.model = Model(name)
        self.ans = self.model.integer_var_matrix(self.n, self.n, 1, self.n, 'ans')
        self.strategy = strategy
        if solve:
            self.ans = self.solve()
        self.check = check
        if solve and check:
            try:
                self.unique = self.check_unique()
            except Exception as e:
                self.unique = f'Error: {e}'

    def parse(self, task):
        raw = ''
        while task:
            if len(task) >= 2 and task[:2].isdigit():
                num = int(task[:2])
                raw += chr(ord('A') + num - 10)
                task = task[2:]
            elif task[0].isdigit():
                num = int(task[0])
                raw += str(num)
                task = task[1:]
            elif task[0].isalpha():
                num = ord(task[0]) - ord('a') + 1
                raw += '.' * num
                task = task[1:]
            elif task[0] == '_':
                task = task[1:]
            else:
                raise ValueError(f"Invalid character '{task[0]}'")
        return raw
    
    def read(self, file):
        if os.path.exists(file):
            with open(file, 'r') as f:
                raw = f.read()
        else:
            raw = self.parse(file)
        # nums = raw.split()
        nums = [x for x in raw if not x.isspace()]
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
                if nums[i*self.n+j].isdigit():
                    self.board[i, j] = int(nums[i*self.n+j])
                elif nums[i*self.n+j].isalpha():
                    self.board[i, j] = ord(nums[i*self.n+j]) - ord('A') + 10
                else:
                    self.board[i, j] = 0
        return self.board
    
    def add_constraints(self):
        self.model.add_constraints([self.ans[i, j] == self.board[i, j] for i in range(self.n) for j in range(self.n) if self.board[i, j] != 0])
        for i in range(self.n):
            for j in range(self.n):
                for k in range(j+1, self.n):
                    self.model.add_constraint(self.ans[i, j] != self.ans[i, k])
                    self.model.add_constraint(self.ans[j, i] != self.ans[k, i])
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
        for i in range(x):
            for j in range(y):
                pairs = [(i*y+k, j*x+l) for k in range(y) for l in range(x)]
                for k in range(len(pairs)):
                    for l in range(k+1, len(pairs)):
                        self.model.add_constraint(self.ans[pairs[k]] != self.ans[pairs[l]])

    def add_constraints_another(self):
        self.model.add_constraints([self.ans[i, j] == self.board[i, j] for i in range(self.n) for j in range(self.n) if self.board[i, j] != 0])
        self.b = self.model.binary_var_cube(self.n, self.n, range(1, self.n+1), 'b')
        for i in range(self.n):
            for j in range(self.n):
                for k in range(1, self.n+1):
                    self.model.add_indicator(self.b[i, j, k], self.ans[i, j] == k)
        for i in range(self.n):
            for k in range(1, self.n+1):
                self.model.add_constraint(self.model.sum(self.b[i, j, k] for j in range(self.n)) == 1)
                self.model.add_constraint(self.model.sum(self.b[j, i, k] for j in range(self.n)) == 1)
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
        for i in range(x):
            for j in range(y):
                pairs = [(i*y+k, j*x+l) for k in range(y) for l in range(x)]
                for k in range(1, self.n+1):
                    self.model.add_constraint(self.model.sum(self.b[p[0], p[1], k] for p in pairs) == 1)
    
    def solve(self):
        if self.strategy == 'another':
            self.add_constraints_another()
        else:
            self.add_constraints()
        self.model.solve()
        return self.ans
    
    def check_unique(self):
        clone = self.__class__(self.file, name=self.name + ' Clone', solve=False, strategy=self.strategy)
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
            res = ''
            for i in range(self.n):
                for j in range(self.n):
                    res += str(round(self.ans[i, j].solution_value)) + ' '
                res += '\n'
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

class Diagonal(Sudoku):
    def __init__(self, file, name='Diagonal Sudoku', check=False, solve=True):
        super().__init__(file, name, check, solve)

    def add_constraints(self):
        super().add_constraints()
        for i in range(self.n):
            for j in range(i+1, self.n):
                self.model.add_constraint(self.ans[i, i] != self.ans[j, j])
                self.model.add_constraint(self.ans[i, self.n-1-i] != self.ans[j, self.n-1-j])



if __name__ == '__main__':
    
    config = {
    'normal': {'class': Sudoku, 'file': 'example/sudoku.txt'},
    'diagonal': {'class': Diagonal, 'file': 'example/diagonal.txt'}
    }

    parser = argparse.ArgumentParser(description='Sudoku Solver')
    parser.add_argument('-f', '--file', type=str, help='File containing the puzzle')
    parser.add_argument('-o', '--output', type=str, help='File to save the solution')
    parser.add_argument('--check', default=False, action='store_true', help='Check if the solution is unique')
    parser.add_argument('--type', type=str, default='normal', help='Type of puzzle', choices=config.keys())
    parser.add_argument('--online', default=False, action='store_true', help='Solve puzzle online')
    parser.add_argument('--diff', type=int, default=0, help='Difficulty of the online puzzle')
    parser.add_argument('-n', type=int, default=1, help='Number of puzzles to solve')
    parser.add_argument('--strategy', type=str, default='default', help='Strategy to solve the puzzle', choices=['default', 'another'])
    
    args = parser.parse_args()
    if args.online:
        os.environ['http_proxy'] = '127.0.0.1:10809'
        os.environ['https_proxy'] = '127.0.0.1:10809'
        url = f'https://www.puzzle-sudoku.com/?size={args.diff}'
        for i in range(args.n):
            task, param = fetch(url)
            solver = config['normal']['class'](task, check=False, strategy=args.strategy)
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
        solver = config[args.type]['class'](args.file, check=args.check, strategy=args.strategy)
        result = solver.pretty()
        if args.output:
            with open(args.output, 'w') as f:
                f.write(result)
        else:
            print(result)