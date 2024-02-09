import argparse
import numpy as np
from docplex.mp.model import Model

class Minesweeper():
    def __init__(self, file, check=False, solve=True):
        self.file = file
        self.n = 0
        self.m = 0
        self.board = self.read(file)
        self.model = Model('Minesweeper')
        self.ans = self.model.binary_var_matrix(self.n, self.n, 'ans')
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
            lines = f.readlines()
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
                    self.model.add_constraint(self.ans[i, j] == 0)
                    pairs = [(i+k, j+l) for k in range(-1, 2) for l in range(-1, 2) if 0 <= i+k < self.n and 0 <= j+l < self.m and (k, l) != (0, 0)]
                    self.model.add_constraint(self.model.sum(self.ans[p] for p in pairs) == self.board[i, j])
    
    def solve(self):
        self.add_constraints()
        self.model.solve()
        return self.ans
    
    def check_unique(self):
        clone = self.__class__(self.file, solve=False)
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
        
    def __str__(self):
        try:
            res = ''
            for i in range(self.n):
                for j in range(self.m):
                    if self.board[i, j] >= 0:
                        res += str(self.board[i, j]) + ' '
                    else:
                        t = int(round(self.ans[i, j].solution_value))
                        res += '* ' if t else '. '
                res += '\n'
            if self.check:
                res += '\n' + self.unique
            return res
        except Exception as e:
            return f'Error: {e}'
        

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MineSweeper Solver')
    parser.add_argument('-f', '--file', type=str, default='example/minesweeper.txt', help='File containing the MineSweeper puzzle')
    parser.add_argument('-o', '--output', type=str, help='File to save the solution')
    parser.add_argument('--check', default=False, action='store_true', help='Check if the solution is unique')

    args = parser.parse_args()
    minesweeper = Minesweeper(args.file, args.check)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(str(minesweeper))
    else:
        print(minesweeper)