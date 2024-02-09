import argparse
from docplex.mp.model import Model
import numpy as np

class Sudoku():
    def __init__(self, file, check=False, solve=True):
        self.file = file
        self.board = self.read(file)
        self.model = Model('Sudoku')
        self.ans = self.model.integer_var_matrix(9, 9, lb=1, ub=9, name='ans')
        if solve:
            self.ans = self.solve()
        self.check = check
        if check:
            self.unique = self.check_unique()
    
    def read(self, file):
        self.board = np.zeros((9, 9), dtype=int)
        with open(file, 'r') as f:
            raw = f.read()
            nums = raw.split()
            if len(nums) != 81:
                raise ValueError(f'Invalid number of entries, expected 81, got {len(nums)}')
            for i in range(9):
                for j in range(9):
                    if nums[i*9+j].isdigit() and 1 <= int(nums[i*9+j]) <= 9:
                        self.board[i, j] = int(nums[i*9+j])
                    else:
                        self.board[i, j] = 0
        return self.board
    
    def solve(self):
        self.model.add_constraints([self.ans[i, j] == self.board[i, j] for i in range(9) for j in range(9) if self.board[i, j] != 0])
        self.model.add_constraints([self.model.sum(self.ans[i, j] for j in range(9)) == 45 for i in range(9)])
        self.model.add_constraints([self.model.sum(self.ans[i, j] for i in range(9)) == 45 for j in range(9)])
        for i in range(3):
            for j in range(3):
                self.model.add_constraint(self.model.sum(self.ans[i*3+k, j*3+l] for k in range(3) for l in range(3)) == 45)
        for i in range(9):
            for j in range(9):
                for k in range(j+1, 9):
                    self.model.add_constraint(self.ans[i, j] != self.ans[i, k])
                    self.model.add_constraint(self.ans[j, i] != self.ans[k, i])
        self.model.solve()
        return self.ans
    
    def check_unique(self):
        clone = Sudoku(self.file, solve=False)
        for i in range(9):
            for j in range(9):
                clone.model.add_constraint(clone.ans[i, j] != int(self.ans[i, j].solution_value))
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
            for i in range(9):
                for j in range(9):
                    res += str(int(self.ans[i, j].solution_value)) + ' '
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