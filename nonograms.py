import os
import argparse
import numpy as np
from online import fetch, submit, hall
from docplex.mp.model import Model

class Nonograms():
    def __init__(self, file, name='Nonograms', check=False, solve=True, strategy='default'):
        self.name = name
        self.file = file
        self.n = 0
        self.m = 0
        self.board = self.read(file)
        self.model = Model(name)
        self.ans = self.model.binary_var_matrix(self.n, self.m, 'ans')
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
        nums = task.split('/')
        if len(nums) % 2:
            raise ValueError(f'Invalid length of task: {len(nums)}')
        cols = nums[:len(nums)//2]
        rows = nums[len(nums)//2:]
        cols = [col.split('.') for col in cols]
        rows = [row.split('.') for row in rows]
        res = 'row\n'
        res += '\n'.join([' '.join(row) for row in rows]) + '\n'
        res += 'col\n'
        res += '\n'.join([' '.join(col) for col in cols]) + '\n'
        return res
    
    def read(self, file):
        if os.path.exists(file):
            with open(file, 'r') as f:
                raw = f.read()
        else:
            raw = self.parse(file)
        lines = raw.split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        lines = ['row' if 'row' in line else 'col' if 'col' in line else line for line in lines]
        irow = lines.index('row')
        icol = lines.index('col')
        if irow < icol:
            rows = lines[irow+1:icol]
            cols = lines[icol+1:]
        else:
            cols = lines[irow+1:icol]
            rows = lines[icol+1:]
        self.n = len(rows)
        self.m = len(cols)
        rows = [list(map(int, row.split())) for row in rows]
        cols = [list(map(int, col.split())) for col in cols]
        self.board = {'row': rows, 'col': cols}
        return self.board
    
    def add_constraints(self):
        self.pos = {'row': {}, 'col': {}}
        self.b = {'row': {}, 'col': {}}
        for i in range(self.n):
            for j in range(len(self.board['row'][i])):
                l = self.board['row'][i][j]
                if l==0:
                    self.model.add_constraint(self.model.sum(self.ans[i, j] for j in range(self.m)) == 0)
                    continue
                self.pos['row'][i, j] = self.model.integer_var(0, self.m-l, f'pos_row_{i}_{j}')
                for k in range(self.m-l+1):
                    self.b['row'][i, j, k] = self.model.binary_var(f'b_row_{i}_{j}_{k}')
                    self.model.add_indicator(self.b['row'][i, j, k], self.pos['row'][i, j] == k)
                    for t in range(l):
                        self.model.add_indicator(self.b['row'][i, j, k], self.ans[i, k+t] == 1)
                self.model.add_constraint(self.model.sum(self.b['row'][i, j, k] for k in range(self.m-l+1)) == 1)
                if j > 0:
                    self.model.add_constraint(self.pos['row'][i, j-1] + self.board['row'][i][j-1] <= self.pos['row'][i, j] - 1)
        for i in range(self.m):
            for j in range(len(self.board['col'][i])):
                l = self.board['col'][i][j]
                if (l==0):
                    self.model.add_constraint(self.model.sum(self.ans[i, j] for i in range(self.n)) == 0)
                    continue
                self.pos['col'][i, j] = self.model.integer_var(0, self.n-l, f'pos_col_{i}_{j}')
                for k in range(self.n-l+1):
                    self.b['col'][i, j, k] = self.model.binary_var(f'b_col_{i}_{j}_{k}')
                    self.model.add_indicator(self.b['col'][i, j, k], self.pos['col'][i, j] == k)
                    for t in range(l):
                        self.model.add_indicator(self.b['col'][i, j, k], self.ans[k+t, i] == 1)
                self.model.add_constraint(self.model.sum(self.b['col'][i, j, k] for k in range(self.n-l+1)) == 1)
                if j > 0:
                    self.model.add_constraint(self.pos['col'][i, j-1] + self.board['col'][i][j-1] <= self.pos['col'][i, j] - 1)
        if self.strategy == 'another':
            obj = self.model.sum(self.ans[i, j] for i in range(self.n) for j in range(self.m))
            self.model.minimize(obj)
        else:
            for i in range(self.n):
                self.model.add_constraint(self.model.sum(self.ans[i, j] for j in range(self.m)) == sum(self.board['row'][i]))
            for j in range(self.m):
                self.model.add_constraint(self.model.sum(self.ans[i, j] for i in range(self.n)) == sum(self.board['col'][j]))

    def solve(self):
        self.add_constraints()
        self.model.solve()
        return self.ans
    
    def check_unique(self):
        clone = self.__class__(self.file, name=self.name + ' Clone', solve=False)
        clone.flag = clone.model.binary_var_matrix(self.n, self.m, 'flag')
        for i in range(self.n):
            for j in range(self.m):
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
                for j in range(self.m):
                    t = round(self.ans[i, j].solution_value)
                    res += '#' if t else '.'
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
                for j in range(self.m):
                    t = round(self.ans[i, j].solution_value)
                    res += 'y' if t else 'n'
            return res
        except Exception as e:
            return f'Error: {e}'
    

if __name__ == '__main__':
    
    config = {
        'normal': {'class': Nonograms, 'file': 'example/nonograms.txt'},
    }

    parser = argparse.ArgumentParser(description='Nonograms Solver')
    parser.add_argument('-f', '--file', type=str, help='File containing the puzzle')
    parser.add_argument('-o', '--output', type=str, help='File to save the solution')
    parser.add_argument('--check', action='store_true', help='Check if the solution is unique')
    parser.add_argument('--type', type=str, default='normal', help='Type of puzzle', choices=config.keys())
    parser.add_argument('--online', action='store_true', help='Solve puzzle online')
    parser.add_argument('--diff', type=int, default=0, help='Difficulty of the online puzzle', choices=range(8))
    parser.add_argument('-n', type=int, default=1, help='Number of puzzles to solve')
    parser.add_argument('--debug', action='store_true', help='Print debug information')
    parser.add_argument('--strategy', type=str, default='default', help='Strategy to solve the puzzle', choices=['default', 'another'])
    
    args = parser.parse_args()
    if args.online:
        os.environ['http_proxy'] = '127.0.0.1:10809'
        os.environ['https_proxy'] = '127.0.0.1:10809'
        url = f'https://www.puzzle-nonograms.com/?size={args.diff}'
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
            if args.debug:
                print(f'task: {task}')
                print(f'parsed: {solver.parse(task)}')
                print(f'result: {result}')
                print(solver.pretty())
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