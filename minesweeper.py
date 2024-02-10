import os
from argparse import ArgumentParser
import numpy as np
from online import fetch, submit, hall
from docplex.mp.model import Model

class Mosaic():
    def __init__(self, file, name='Mosaic', check=False, solve=True):
        self.name = name
        self.file = file
        self.n = 0
        self.m = 0
        self.board = self.read(file)
        self.model = Model(name)
        self.ans = self.model.binary_var_matrix(self.n, self.n, 'ans')
        if solve:
            self.ans = self.solve()
        self.check = check
        if solve and check:
            try:
                self.unique = self.check_unique()
            except Exception as e:
                self.unique = f'Error: {e}'

    def parse(self, task):
        for i in range(26):
            task = task.replace(chr(ord('a') + i), '.'*(i+1))
        n = round(np.sqrt(len(task)))
        if n * n != len(task):
            raise ValueError(f'Invalid length of task: {len(task)}')
        task = '\n'.join([task[i*n:(i+1)*n] for i in range(n)])
        return task
    
    def read(self, file):
        if os.path.exists(file):
            with open(file, 'r') as f:
                raw = f.read()
        else:
            raw = self.parse(file)
        lines = raw.split('\n')
        lines = [line.strip().replace(' ', '').replace('\t', '') for line in lines if line.strip()]
        self.n = len(lines)
        self.m = max([len(line) for line in lines])
        self.board = np.zeros((self.n, self.m), dtype=int)
        for i in range(self.n):
            for j in range(len(lines[i])):
                if lines[i][j].isdigit():
                    self.board[i, j] = int(lines[i][j])
                else:
                    self.board[i, j] = -1
        return self.board
    
    def add_constraints(self):
        for i in range(self.n):
            for j in range(self.m):
                if self.board[i, j] != -1:
                    # self.model.add_constraint(self.ans[i, j] == 0)
                    pairs = [(i+k, j+l) for k in range(-1, 2) for l in range(-1, 2) if 0 <= i+k < self.n and 0 <= j+l < self.m]
                    self.model.add_constraint(self.model.sum(self.ans[p] for p in pairs) == self.board[i, j])
    
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
        result = str(clone)
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
                    res += '* ' if t else '. '
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

class MineSweeper(Mosaic):
    def __init__(self, file, name='MineSweeper', check=False, solve=True):
        super().__init__(file, name, check, solve)
    
    def add_constraints(self):
        super().add_constraints()
        for i in range(self.n):
            for j in range(self.m):
                if self.board[i, j] != -1:
                    self.model.add_constraint(self.ans[i, j] == 0)

    def pretty(self):
        try:
            res = ''
            for i in range(self.n):
                for j in range(self.m):
                    if self.board[i, j] >= 0:
                        res += str(self.board[i, j]) + ' '
                    else:
                        t = round(self.ans[i, j].solution_value)
                        res += '* ' if t else '. '
                res += '\n'
            if self.check:
                res += '\n' + self.unique
            return res
        except Exception as e:
            return f'Error: {e}'


if __name__ == '__main__':

    config = {
        'minesweeper': {'class': MineSweeper, 'file': 'example/minesweeper.txt'},
        'mosaic': {'class': Mosaic, 'file': 'example/mosaic.txt'}
    }

    parser = ArgumentParser(description='MineSweeper Solver')
    parser.add_argument('-f', '--file', type=str, help='File containing the puzzle')
    parser.add_argument('-o', '--output', type=str, help='File to save the solution')
    parser.add_argument('--check', action='store_true', help='Check if the solution is unique')
    parser.add_argument('--type', type=str, default='minesweeper', help='Type of puzzle', choices=config.keys())
    parser.add_argument('--online', action='store_true', help='Solve puzzle online')
    parser.add_argument('--size', type=int, default=5, help='Size of the puzzle', choices=[5, 7, 10, 15, 20])
    parser.add_argument('--diff', type=str, default='easy', help='Difficulty of the online puzzle', choices=['easy', 'hard', 'daily', 'weekly', 'monthly'])
    parser.add_argument('-n', type=int, default=1, help='Number of puzzles to solve')
    parser.add_argument('--debug', action='store_true', help='Print debug information')

    args = parser.parse_args()
    if args.online:
        os.environ['http_proxy'] = '127.0.0.1:10809'
        os.environ['https_proxy'] = '127.0.0.1:10809'
        if args.diff in ['daily', 'weekly', 'monthly']:
            url = f'https://www.puzzle-minesweeper.com/{args.diff}-{args.type}/'
        else:
            url = f'https://www.puzzle-minesweeper.com/{args.type}-{args.size}x{args.size}-{args.diff}/'
        for i in range(args.n):
            task, param = fetch(url)
            solver = config[args.type]['class'](task, name=args.type, check=args.check)
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
        solver = config[args.type]['class'](args.file, name=args.type, check=args.check)
        result = solver.pretty()
        if args.output:
            with open(args.output, 'w') as f:
                f.write(result)
        else:
            print(result)