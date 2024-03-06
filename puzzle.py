import os
import numpy as np
from argparse import ArgumentParser
from online import fetch, submit, hall
import gurobipy as gp
from gurobipy import GRB

class Puzzle():
    def __init__(self, input, name, check=False, solve=True, strategy='default', debug=False):
        self.name = name
        self.debug = debug
        self.input = input
        self.strategy = strategy
        self.check = check
        self.model = gp.Model(name)
        if debug:
            print(f'Name: {self.name}\nInput: {self.input}\nSolve: {solve}\nCheck: {check}\nStrategy: {strategy}')
        else:
            self.model.params.OutputFlag = 0
        self.board = self.read(self.input)
        self.init_board()
        if solve:
            self.ans = self.solve()
        if solve and check:
            try:
                self.unique = self.check_unique()
            except Exception as e:
                if debug:
                    raise e
                self.unique = f'Error: {e}'
    
    def init_board(self):
        raise NotImplementedError

    def parse_from_task(self, task):
        raise NotImplementedError
    
    def parse_from_file(self, file):
        raise NotImplementedError
    
    def read(self, input):
        if os.path.exists(input):
            self.board = self.parse_from_file(input)
        else:
            self.board = self.parse_from_task(input)
        if self.debug:
            print(f"Borad: {str(self.board).replace('\n', '')}")
        return self.board
        
    def strategy_default(self):
        raise NotImplementedError
    
    def strategy_bank(self):
        return {'default': self.strategy_default}
    
    def solve(self):
        self.strategy_bank()[self.strategy]()
        self.model.optimize()
        return self.ans
    
    def init_clone(self):
        raise NotImplementedError
    
    def check_unique(self):
        self.clone = self.__class__(self.input, name=self.name + ' Clone', solve=False, strategy=self.strategy, debug=self.debug)
        self.init_clone()
        self.clone.ans = self.clone.solve()
        result = self.clone.pretty()
        if 'Error' in result:
            return 'The solution is unique'
        else:
            return 'The solution is not unique\n' + result
    
    def pretty(self):
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError

class PuzzleParser(ArgumentParser):
    def __init__(self, description='Puzzle Solver', default='normal'):
        super().__init__(description=description)
        self.config = self.init_config()
        self.add_argument('-f', '--file', type=str, help='File containing the puzzle')
        self.add_argument('-o', '--output', type=str, help='File to save the solution')
        self.add_argument('--type', type=str, default=default, help='Type of puzzle', choices=self.config.keys())
        self.add_argument('--check', action='store_true', help='Check if the solution is unique')
        self.add_argument('--strategy', type=str, default='default', help='Strategy to solve the puzzle')
        self.add_argument('--debug', action='store_true', help='Print debug information')
        self.add_argument('--online', action='store_true', help='Solve puzzle online')
        self.add_argument('-n', type=int, default=1, help='Number of puzzles to solve')
        self.add_extra_args()

    def init_config(self):
        raise NotImplementedError
    
    def add_extra_args(self):
        self.add_argument('--domain', type=str, default='puzzle-sudoku', help='Domain of the online puzzle')
        self.add_argument('--diff', type=int, default=0, help='Difficulty of the online puzzle')
    
    def url(self):
        return f"https://www.{self.args.domain}.com/?size={self.args.diff}"
    
    def main(self):
        self.args = self.parse_args()
        if self.args.online:
            url = self.url()
            for i in range(self.args.n):
                task, param = fetch(url)
                solver_class = self.config[self.args.type]['class']
                solver = solver_class(task, check=False, strategy=self.args.strategy)
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
                if self.args.debug:
                    print(f'task: {task}')
                    # print(f'parsed: {solver.parse(task)}')
                    print(f'result: {result}')
                    print(solver.pretty())
        else:
            if not self.args.file:
                self.args.file = self.config[self.args.type]['file']
            solver_class = self.config[self.args.type]['class']
            solver = solver_class(self.args.file, check=self.args.check, strategy=self.args.strategy, debug=self.args.debug)
            result = solver.pretty()
            if self.args.output:
                with open(self.args.output, 'w') as f:
                    f.write(result)
            else:
                print(result)


if __name__ == '__main__':
    parser = PuzzleParser()
    parser.main()