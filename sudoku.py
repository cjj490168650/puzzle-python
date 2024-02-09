import argparse
import numpy as np
from docplex.mp.model import Model

class Sudoku():
    def __init__(self, file, check=False, solve=True):
        self.file = file
        self.n = 9
        self.board = self.read(file)
        self.model = Model('Sudoku')
        self.ans = self.model.integer_var_matrix(self.n, self.n, 1, self.n, 'ans')
        if solve:
            self.ans = self.solve()
        self.check = check
        if check:
            self.unique = self.check_unique()
    
    def read(self, file):
        self.board = None
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
        clone = Sudoku(self.file, solve=False)
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sudoku Solver')
    parser.add_argument('-f', '--file', type=str, default='example/sudoku.txt', help='File containing the sudoku puzzle')
    parser.add_argument('-o', '--output', type=str, help='Output file to write the solution')
    parser.add_argument('--check', default=False, action='store_true', help='Check if the solution is unique')
    args = parser.parse_args()
    sudoku = Sudoku(args.file, check=args.check)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(str(sudoku))
    else:
        print(sudoku)