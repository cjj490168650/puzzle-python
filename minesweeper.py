import os
import numpy as np
from puzzle import Puzzle, PuzzleParser
from argparse import ArgumentParser
from online import fetch, submit, hall
import gurobipy as gp
from gurobipy import GRB

class Mosaic(Puzzle):
    def __init__(self, input, name='Mosaic', check=False, solve=True, strategy='default', debug=False):
        super().__init__(input, name, check, solve, strategy, debug)

    def init_board(self):
        self.ans = self.model.addVars(self.n, self.m, vtype=GRB.BINARY, name='ans')
    
    def parse_lines(self, lines):
        self.n = len(lines)
        self.m = max([len(lines) for line in lines])
        self.board = np.zeros((self.n, self.m), dtype=int)
        for i in range(self.n):
            for j in range(len(lines[i])):
                self.board[i, j] = lines[i][j]
        return self.board

    def parse_from_task(self, task):
        lines = []
        for i in range(26):
            task = task.replace(chr(ord('a') + i), '.'*(i+1))
        n = round(np.sqrt(len(task)))
        if n * n != len(task):
            raise ValueError(f'Invalid length of task: {len(task)}')
        for i in range(n):
            line = [int(x) if x.isdigit() else -1 for x in task[i*n:(i+1)*n]]
            lines.append(line)
        return self.parse_lines(lines)
    
    def parse_from_file(self, file):
        with open(file, 'r') as f:
            raw = f.read()
        raws = raw.split('\n')
        raws = [line.strip().replace(' ', '').replace('\t', '') for line in raws if line.strip()]
        lines = []
        for line in raws:
            line = [int(x) if x.isdigit() else -1 for x in line]
            lines.append(line)
        return self.parse_lines(lines)
    
    def strategy_default(self):
        for i in range(self.n):
            for j in range(self.m):
                if self.board[i, j] != -1:
                    pairs = [(i+k, j+l) for k in range(-1, 2) for l in range(-1, 2) if 0 <= i+k < self.n and 0 <= j+l < self.m]
                    self.model.addConstr(gp.quicksum(self.ans[p] for p in pairs) == self.board[i, j])
    
    def init_clone(self):
        self.clone.neq = self.clone.model.addVars(self.n, self.m, vtype=GRB.BINARY, name='flag')
        for i in range(self.n):
            for j in range(self.m):
                self.clone.model.addConstr((self.clone.neq[i, j] == 1) >> (self.clone.ans[i, j] + round(self.ans[i, j].X) == 1))
        self.clone.model.addConstr(self.clone.neq.sum() >= 1)
    
    def pretty(self):
        try:
            res = ''
            for i in range(self.n):
                for j in range(self.m):
                    t = round(self.ans[i, j].X)
                    res += '* ' if t else '. '
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
                for j in range(self.m):
                    t = round(self.ans[i, j].X)
                    res += 'y' if t else 'n'
            return res
        except Exception as e:
            if self.debug:
                raise e
            return f'Error: {e}'

class MineSweeper(Mosaic):
    def __init__(self, file, name='MineSweeper', check=False, solve=True, strategy='default', debug=False):
        super().__init__(file, name, check, solve, strategy, debug)
    
    def strategy_default(self):
        super().strategy_default()
        for i in range(self.n):
            for j in range(self.m):
                if self.board[i, j] != -1:
                    self.model.addConstr(self.ans[i, j] == 0)

    def pretty(self):
        try:
            res = ''
            for i in range(self.n):
                for j in range(self.m):
                    if self.board[i, j] >= 0:
                        res += str(self.board[i, j]) + ' '
                    else:
                        t = round(self.ans[i, j].X)
                        res += '* ' if t else '. '
                res += '\n'
            if self.check:
                res += '\n' + self.unique
            return res
        except Exception as e:
            if self.debug:
                raise e
            return f'Error: {e}'
        
class MosaicParser(PuzzleParser):
    def __init__(self, description='Mosaic Solver', default='minesweeper'):
        super().__init__(description, default)

    def init_config(self):
        return {'minesweeper': {'class': MineSweeper, 'file': 'example/minesweeper.txt'},
                'mosaic': {'class': Mosaic, 'file': 'example/mosaic.txt'}}
    
    def add_extra_args(self):
        '''
        0: 5x5 Easy Minesweeper
        1: 5x5 Hard Minesweeper
        2: 7x7 Easy Minesweeper
        3: 7x7 Hard Minesweeper
        4: 10x10 Easy Minesweeper
        5: 10x10 Hard Minesweeper
        6: 15x15 Easy Minesweeper
        7: 15x15 Hard Minesweeper
        8: 20x20 Easy Minesweeper
        9: 20x20 Hard Minesweeper
        10: Special Daily Minesweeper
        11: Special Weekly Minesweeper
        12: Special Monthly Minesweeper
        '''
        self.add_argument('--domain', type=str, default='puzzle-minesweeper', help='Domain of the online puzzle')
        self.add_argument('--size', type=int, default=5, help='Size of the puzzle', choices=[5, 7, 10, 15, 20])
        self.add_argument('--diff', type=str, default='easy', help='Difficulty of the online puzzle', choices=['easy', 'hard', 'daily', 'weekly', 'monthly'])

    def url(self):
        if self.args.diff in ['daily', 'weekly', 'monthly']:
            url = f'https://www.{self.args.domain}.com/{self.args.diff}-{self.args.type}/'
        else:
            url = f'https://www.{self.args.domain}.com/{self.args.type}-{self.args.size}x{self.args.size}-{self.args.diff}/'
        return url
    

if __name__ == '__main__':
    parser = MosaicParser()
    parser.main()