import os
import numpy as np
from puzzle import Puzzle, PuzzleParser
from argparse import ArgumentParser
from online import fetch, submit, hall
import gurobipy as gp
from gurobipy import GRB

class Nonograms(Puzzle):
    def __init__(self, input, name='Nonograms', check=False, solve=True, strategy='default', debug=False):
        super().__init__(input, name, check, solve, strategy, debug)

    def init_board(self):
        self.ans = self.model.addVars(self.n, self.m, vtype=GRB.BINARY, name='ans')

    def parse(self, raw):
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
        rows = [[int(x) if x.isdigit() else -1 for x in row.split()] for row in rows]
        cols = [[int(x) if x.isdigit() else -1 for x in col.split()] for col in cols]
        self.board = {'row': rows, 'col': cols}
        return self.board
    
    def parse_from_task(self, task):
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
        return self.parse(res)

    def parse_from_file(self, file):
        with open(file, 'r') as f:
            raw = f.read()
        return self.parse(raw)
    
    def strategy_common(self):
        self.pos = {'row': {}, 'col': {}}
        for i in range(self.n):
            for j in range(len(self.board['row'][i])):
                l = self.board['row'][i][j]
                if l==-1:
                    raise NotImplementedError
                if l==0:
                    self.model.addConstr(gp.quicksum(self.ans[i, j] for j in range(self.m)) == 0)
                    continue
                pre = sum(self.board['row'][i][:j]) + j
                suf = sum(self.board['row'][i][j+1:]) + len(self.board['row'][i]) - j - 1
                self.pos['row'][i, j] = self.model.addVar(pre, self.m-suf-l, vtype=GRB.INTEGER, name=f'pos_row_{i}_{j}')
                if j > 0:
                    self.model.addConstr(self.pos['row'][i, j-1] + self.board['row'][i][j-1] <= self.pos['row'][i, j] - 1)
        for i in range(self.m):
            for j in range(len(self.board['col'][i])):
                l = self.board['col'][i][j]
                if l==-1:
                    raise NotImplementedError
                if l==0:
                    self.model.addConstr(gp.quicksum(self.ans[i, j] for i in range(self.n)) == 0)
                    continue
                pre = sum(self.board['col'][i][:j]) + j
                suf = sum(self.board['col'][i][j+1:]) + len(self.board['col'][i]) - j - 1
                self.pos['col'][i, j] = self.model.addVar(pre, self.n-suf-l, vtype=GRB.INTEGER, name=f'pos_col_{i}_{j}')
                if j > 0:
                    self.model.addConstr(self.pos['col'][i, j-1] + self.board['col'][i][j-1] <= self.pos['col'][i, j] - 1)

    def strategy_default(self):
        self.strategy_common()
        self.cmpl = {}
        self.cmpr = {}
        self.cmp = {}
        for i in range(self.n):
            for k in range(len(self.board['row'][i])):
                l = self.board['row'][i][k]
                if l==-1:
                    raise NotImplementedError
                if l==0:
                    continue
                for j in range(self.m):
                    self.cmpl[i, j, 'r', k] = self.model.addVar(vtype=GRB.BINARY, name=f'cmpl_{i}_{j}_r_{k}')
                    self.cmpr[i, j, 'r', k] = self.model.addVar(vtype=GRB.BINARY, name=f'cmpr_{i}_{j}_r_{k}')
                    self.cmp[i, j, 'r', k] = self.model.addVar(vtype=GRB.BINARY, name=f'cmp_{i}_{j}_r_{k}')
                    self.model.addConstr((self.cmpl[i, j, 'r', k] == 1) >> (j >= self.pos['row'][i, k]))
                    self.model.addConstr((self.cmpl[i, j, 'r', k] == 0) >> (j <= self.pos['row'][i, k] - 1))
                    self.model.addConstr((self.cmpr[i, j, 'r', k] == 1) >> (j <= self.pos['row'][i, k] + l - 1))
                    self.model.addConstr((self.cmpr[i, j, 'r', k] == 0) >> (j >= self.pos['row'][i, k] + l))
                    self.model.addConstr(self.cmp[i, j, 'r', k] == gp.and_(self.cmpl[i, j, 'r', k], self.cmpr[i, j, 'r', k]))
        for j in range(self.m):
            for k in range(len(self.board['col'][j])):
                l = self.board['col'][j][k]
                if l==-1:
                    raise NotImplementedError
                if l==0:
                    continue
                for i in range(self.n):
                    self.cmpl[i, j, 'c', k] = self.model.addVar(vtype=GRB.BINARY, name=f'cmpl_{i}_{j}_c_{k}')
                    self.cmpr[i, j, 'c', k] = self.model.addVar(vtype=GRB.BINARY, name=f'cmpr_{i}_{j}_c_{k}')
                    self.cmp[i, j, 'c', k] = self.model.addVar(vtype=GRB.BINARY, name=f'cmp_{i}_{j}_c_{k}')
                    self.model.addConstr((self.cmpl[i, j, 'c', k] == 1) >> (i >= self.pos['col'][j, k]))
                    self.model.addConstr((self.cmpl[i, j, 'c', k] == 0) >> (i <= self.pos['col'][j, k] - 1))
                    self.model.addConstr((self.cmpr[i, j, 'c', k] == 1) >> (i <= self.pos['col'][j, k] + l - 1))
                    self.model.addConstr((self.cmpr[i, j, 'c', k] == 0) >> (i >= self.pos['col'][j, k] + l))
                    self.model.addConstr(self.cmp[i, j, 'c', k] == gp.and_(self.cmpl[i, j, 'c', k], self.cmpr[i, j, 'c', k]))
        for i in range(self.n):
            for j in range(self.m):
                if 0 not in self.board['row'][i]:
                    self.model.addConstr(self.ans[i, j] == gp.or_(self.cmp[i, j, 'r', k] for k in range(len(self.board['row'][i]))))
                if 0 not in self.board['col'][j]:
                    self.model.addConstr(self.ans[i, j] == gp.or_(self.cmp[i, j, 'c', k] for k in range(len(self.board['col'][j]))))
                
    def strategy_b(self):
        self.strategy_common()
        self.b = {'row': {}, 'col': {}}
        for i in range(self.n):
            for j in range(len(self.board['row'][i])):
                l = self.board['row'][i][j]
                if l==-1:
                    raise NotImplementedError
                if l==0:
                    continue
                pre = sum(self.board['row'][i][:j]) + j
                suf = sum(self.board['row'][i][j+1:]) + len(self.board['row'][i]) - j - 1
                for k in range(pre, self.m-suf-l+1):
                    self.b['row'][i, j, k] = self.model.addVar(vtype=GRB.BINARY, name=f'b_row_{i}_{j}_{k}')
                    self.model.addConstr((self.b['row'][i, j, k] == 1) >> (self.pos['row'][i, j] == k))
                    for t in range(l):
                        self.model.addConstr((self.b['row'][i, j, k] == 1) >> (self.ans[i, k+t] == 1))
                self.model.addConstr(gp.quicksum(self.b['row'][i, j, k] for k in range(pre, self.m-suf-l+1)) == 1)
        for i in range(self.m):
            for j in range(len(self.board['col'][i])):
                l = self.board['col'][i][j]
                if l==-1:
                    raise NotImplementedError
                if l==0:
                    continue
                pre = sum(self.board['col'][i][:j]) + j
                suf = sum(self.board['col'][i][j+1:]) + len(self.board['col'][i]) - j - 1
                for k in range(pre, self.n-suf-l+1):
                    self.b['col'][i, j, k] = self.model.addVar(vtype=GRB.BINARY, name=f'b_col_{i}_{j}_{k}')
                    self.model.addConstr((self.b['col'][i, j, k] == 1) >> (self.pos['col'][i, j] == k))
                    for t in range(l):
                        self.model.addConstr((self.b['col'][i, j, k] == 1) >> (self.ans[k+t, i] == 1))
                self.model.addConstr(gp.quicksum(self.b['col'][i, j, k] for k in range(pre, self.n-suf-l+1)) == 1)
    
    def strategy_bdefault(self):
        self.strategy_b()
        for i in range(self.n):
            self.model.addConstr(gp.quicksum(self.ans[i, j] for j in range(self.m)) == sum(self.board['row'][i]))
        for j in range(self.m):
            self.model.addConstr(gp.quicksum(self.ans[i, j] for i in range(self.n)) == sum(self.board['col'][j]))
    
    def strategy_bminimize(self):
        self.strategy_b()
        obj = gp.quicksum(self.ans[i, j] for i in range(self.n) for j in range(self.m))
        self.model.setObjective(obj, GRB.MINIMIZE)

    def strategy_bank(self):
        return {'default': self.strategy_default, 'b': self.strategy_bdefault, 'bmin': self.strategy_bminimize}
    
    def init_clone(self):
        self.clone.neq = self.clone.model.addVars(self.n, self.m, vtype=GRB.BINARY, name='neq')
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
                    res += '#' if t else '.'
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

class NonogramsParser(PuzzleParser):
    def __init__(self):
        super().__init__(description='Nonograms Solver')
    
    def init_config(self):
        return {'normal': {'class': Nonograms, 'file': 'example/nonograms.txt'}}
    
    def add_extra_args(self):
        '''
        0: 5x5 Nonograms
        1: 10x10 Nonograms
        2: 15x15 Nonograms
        3: 20x20 Nonograms
        4: 25x25 Nonograms
        5: Special Daily Nonograms
        6: Special Weekly Nonograms
        7: Special Monthly Nonograms
        '''
        self.add_argument('--domain', type=str, default='puzzle-nonograms', help='Domain of the online puzzle')
        self.add_argument('--diff', type=int, default=0, help='Difficulty of the online puzzle', choices=range(8))

if __name__ == '__main__':
    parser = NonogramsParser()
    parser.main()