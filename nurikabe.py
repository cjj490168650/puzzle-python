import os
import numpy as np
from puzzle import Puzzle, PuzzleParser
from argparse import ArgumentParser
from online import fetch, submit, hall
import gurobipy as gp
from gurobipy import GRB
from board import Board

class Nurikabe(Puzzle):
    def __init__(self, input, name='Nurikabe', check=False, solve=True, strategy='default', debug=False):
        self.name = name
        self.debug = debug
        self.input = input
        self.strategy = strategy
        self.check = check
        if debug:
            print(f'Name: {self.name}\nInput: {self.input}\nSolve: {solve}\nCheck: {check}\nStrategy: {strategy}')
        self.board = self.read(self.input)
        if solve:
            self.board.solve()
        if solve and check:
            try:
                self.unique = self.check_unique()
            except Exception as e:
                if debug:
                    raise e
                self.unique = f'Error: {e}'

    def parse_from_task(self, task):
        self.raw = []
        while task:
            if task[0] == '_':
                task = task[1:]
            if len(task) >= 2 and task[:2].isdigit():
                self.raw.append(int(task[:2]))
                task = task[2:]
            elif task[0].isdigit():
                self.raw.append(int(task[0]))
                task = task[1:]
            else:
                cnt = ord(task[0]) - ord('a') + 1
                self.raw += [0] * cnt
                task = task[1:]
        self.n = round(np.sqrt(len(self.raw)))
        if self.n * self.n != len(self.raw):
            raise ValueError(f'Invalid length of task: {len(self.raw)}')
        self.board = Board(self.n, self.n, self.name)
        if not self.debug:
            self.board.model.setParam('OutputFlag', 0)
        for x in range(self.n):
            for y in range(self.n):
                c = self.raw[x * self.n + y]
                if c:
                    self.board.clue_size(x, y, int(c))
        self.board.rule_connected(1)
        self.board.rule_no2x2()
        self.board.rule_allmarked(0)
        return self.board
    
    def pretty(self):
        try:
            res = ''
            for i in range(self.n):
                for j in range(self.n):
                    if self.raw[i * self.n + j]:
                        if self.raw[i * self.n + j] >= 10:
                            res += chr(ord('A') + self.raw[i * self.n + j] - 10)
                        else:
                            res += str(self.raw[i * self.n + j])
                    elif self.board.ans[i, j].X > 0.5:
                        res += '#'
                    else:
                        res += '.'
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
                    if self.board.ans[i, j].X > 0.5:
                        res += 'y'
                    else:
                        res += 'n'
            return res
        except Exception as e:
            if self.debug:
                raise e
            return f'Error: {e}'

class NurikabeParser(PuzzleParser):
    def __init__(self, description='Nurikabe Solver'):
        super().__init__(description)
    
    def init_config(self):
        return {'normal': {'class': Nurikabe, 'file': 'default'}}
    
    def add_extra_args(self):
        '''
        0: 5x5 Easy Nurikabe
        6: 5x5 Hard Nurikabe
        1: 7x7 Easy Nurikabe
        7: 7x7 Hard Nurikabe
        2: 10x10 Easy Nurikabe
        8: 10x10 Hard Nurikabe
        5: 12x12 Easy Nurikabe
        9: 12x12 Hard Nurikabe
        3: 15x15 Easy Nurikabe
        10: 15x15 Hard Nurikabe
        4: 20x20 Easy Nurikabe
        11: Special Daily Nurikabe
        12: Special Weekly Nurikabe
        13: Special Monthly Nurikabe
        '''
        self.add_argument('--domain', type=str, default='puzzle-nurikabe', help='Domain of the online puzzle')
        self.add_argument('--diff', type=int, default=0, help='Difficulty of the online puzzle', choices=range(14))


if __name__ == '__main__':
    parser = NurikabeParser()
    parser.main()
    # solver = Nurikabe('r3c4a1a3c4r')
    # solver.board.solve()
    # print(solver.pretty())