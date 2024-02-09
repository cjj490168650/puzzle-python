import argparse
import numpy as np
from docplex.mp.model import Model

class Sudoku():
    def __init__(self, file, name='Sudoku', check=False, solve=True):
        self.name = name
        self.file = file
        self.n = 9
        self.board = self.read(file)
        self.model = Model(name)
        self.ans = self.model.integer_var_matrix(self.n, self.n, 1, self.n, 'ans')
        if solve:
            self.ans = self.solve()
        self.check = check
        if check:
            try:
                self.unique = self.check_unique()
            except Exception as e:
                self.unique = f'Error: {e}'
    
    def read(self, file):
        with open(file, 'r') as f:
            raw = f.read()
            # nums = raw.split()
            nums = [x for x in raw if not x.isspace()]
            if len(nums) == 36:
                self.n = 6
            elif len(nums) == 81:
                self.n = 9
            else:
                raise ValueError(f'Invalid number of entries, expected 36 or 81, got {len(nums)}')
            self.board = np.zeros((self.n, self.n), dtype=int)
            for i in range(self.n):
                for j in range(self.n):
                    if nums[i*self.n+j].isdigit() and 1 <= int(nums[i*self.n+j]) <= self.n:
                        self.board[i, j] = int(nums[i*self.n+j])
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
            for i in range(3):
                for j in range(2):
                    pairs = [(i*2+k, j*3+l) for k in range(2) for l in range(3)]
                    for k in range(len(pairs)):
                        for l in range(k+1, len(pairs)):
                            self.model.add_constraint(self.ans[pairs[k]] != self.ans[pairs[l]])
        else:
            for i in range(3):
                for j in range(3):
                    pairs = [(i*3+k, j*3+l) for k in range(3) for l in range(3)]
                    for k in range(len(pairs)):
                        for l in range(k+1, len(pairs)):
                            self.model.add_constraint(self.ans[pairs[k]] != self.ans[pairs[l]])
    
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
        result = str(clone)
        if 'did not solve successfully' in result:
            return 'The solution is unique'
        elif 'Error' in result:
            return f'Error: {result}'
        else:
            return 'The solution is not unique\n' + result
    
    def __str__(self):
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
    parser = argparse.ArgumentParser(description='Sudoku Solver')
    parser.add_argument('-f', '--file', type=str, help='File containing the Sudoku puzzle')
    parser.add_argument('-o', '--output', type=str, help='File to save the solution')
    parser.add_argument('--check', default=False, action='store_true', help='Check if the solution is unique')
    parser.add_argument('--type', type=str, default='normal', help='Type of puzzle', choices=['normal', 'diagonal'])
    
    args = parser.parse_args()
    if not args.file:
        defaults = {'normal': 'example/sudoku.txt', 
                    'diagonal': 'example/sudoku_diagonal.txt'}
        args.file = defaults[args.type]
    types = {'normal': Sudoku, 'diagonal': Diagonal}
    solver = types[args.type](args.file, check=args.check)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(str(solver))
    else:
        print(solver)