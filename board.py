import gurobipy as gp
from gurobipy import GRB, Model
import numpy as np

class Board:
    def __init__(self, n, m=0, name='Board'):
        if m == 0:
            m = n
        self.n = n
        self.m = m
        self.name = name
        self.model = Model(name)
        self.ans = self.model.addVars(n, m, vtype=GRB.BINARY, name='ans')
        self.clues = {}
        self.add_cut(self.ans, 'ans')
        self.add_cnt(0)
        self.add_cnt(1)

    def adj(self, x, y):
        res = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            if 0 <= x + dx < self.n and 0 <= y + dy < self.m:
                res.append((x + dx, y + dy))
        return res
    
    def add_cut(self, b, key):
        try:
            self.is_cut
        except:
            self.is_cut = {}
        tag = str(key).replace(' ', '')
        self.is_cut[key] = {}
        for x in range(self.n):
            for y in range(self.m):
                for xx, yy in self.adj(x, y):
                    self.is_cut[key][x, y, xx, yy] = self.model.addVar(vtype=GRB.BINARY, name=f'is_cut_{tag}[{x},{y},{xx},{yy}]')
                    self.model.addConstr(self.is_cut[key][x, y, xx, yy] <= b[x, y] + b[xx, yy])
                    self.model.addConstr(self.is_cut[key][x, y, xx, yy] <= 2 - b[x, y] - b[xx, yy])
                    self.model.addConstr(self.is_cut[key][x, y, xx, yy] >= b[x, y] - b[xx, yy])
                    self.model.addConstr(self.is_cut[key][x, y, xx, yy] >= b[xx, yy] - b[x, y])

    def add_e(self, key, cutter):
        try:
            self.e
        except:
            self.e = {}
            self.sum_in = {}
            self.sum_out = {}
        tag = str(key).replace(' ', '')
        self.e[key] = {}
        self.sum_in[key] = self.model.addVars(self.n, self.m, vtype=GRB.INTEGER, name=f'sum_in_{tag}')
        self.sum_out[key] = self.model.addVars(self.n, self.m, vtype=GRB.INTEGER, name=f'sum_out_{tag}')
        for x in range(self.n):
            for y in range(self.m):
                for xx, yy in self.adj(x, y):
                    self.e[key][x, y, xx, yy] = self.model.addVar(vtype=GRB.INTEGER, lb=0, name=f'e_{tag}[{x},{y},{xx},{yy}]')
                    self.model.addConstr((self.is_cut[cutter][x, y, xx, yy] == 1) >> (self.e[key][x, y, xx, yy] == 0))
                    # self.model.addConstr((self.is_cut[cutter][x, y, xx, yy] == 0) >> (self.e[name][x, y, xx, yy] >= 1))
        for x in range(self.n):
            for y in range(self.m):
                self.model.addConstr(self.sum_out[key][x, y] == gp.quicksum(self.e[key][x, y, xx, yy] for xx, yy in self.adj(x, y)))
                self.model.addConstr(self.sum_in[key][x, y] == gp.quicksum(self.e[key][xx, yy, x, y] for xx, yy in self.adj(x, y)))
    
    def add_cnt(self, color):
        try:
            self.cnt
        except:
            self.cnt = {}
        self.cnt[color] = self.model.addVar(vtype=GRB.INTEGER, name=f'cnt_{color}')
        if color == 0:
            self.model.addConstr(self.cnt[color] == self.n * self.m - self.ans.sum())
        else:
            self.model.addConstr(self.cnt[color] == self.ans.sum())
    
    def clue_color(self, x, y, color):
        self.clues[x, y] = {"color": color}
        self.model.addConstr(self.ans[x, y] == color)

    def clue_size(self, x, y, size, color=0):
        self.clues[x, y] = {"size": size}
        if color >= 0:
            self.clues[x, y]["color"] = color
        try:
            self.s
        except:
            self.s = {}
            self.t = {}
        try:
            self.is_belong
        except:
            self.is_belong = {}
        if color >= 0:
            self.model.addConstr(self.ans[x, y] == color)
        tag = f'({x},{y})'
        self.is_belong[x, y] = self.model.addVars(self.n, self.m, vtype=GRB.BINARY, name=f'is_belong_{tag}')
        self.s[x, y] = self.model.addVars(self.n, self.m, vtype=GRB.BINARY, name=f's_{tag}')
        self.t[x, y] = self.model.addVars(self.n, self.m, vtype=GRB.BINARY, name=f't_{tag}')
        self.model.addConstr(self.s[x, y][x, y] == 1)
        self.model.addConstrs((self.s[x, y][xx, yy] == 0) for xx in range(self.n) for yy in range(self.m) if (xx, yy) != (x, y))
        self.model.addConstr(self.t[x, y].sum() == size - 1)
        self.model.addConstrs(self.is_belong[x, y][xx, yy] == self.s[x, y][xx, yy] + self.t[x, y][xx, yy] for xx in range(self.n) for yy in range(self.m))
        self.add_cut(self.is_belong[x, y], (x, y))
        self.add_e((x, y), (x, y))
        self.model.addConstr(self.sum_out[x, y][x, y] == self.sum_in[x, y][x, y] + size - 1)
        for xx in range(self.n):
            for yy in range(self.m):
                self.model.addConstr((self.is_belong[x, y][xx, yy] == 1) >> (self.ans[xx, yy] == self.ans[x, y]))
                self.model.addConstr((self.t[x, y][xx, yy] == 1) >> (self.sum_out[x, y][xx, yy] == self.sum_in[x, y][xx, yy] - 1))
                if abs(xx - x) + abs(yy - y) >= size:
                    self.model.addConstr(self.t[x, y][xx, yy] == 0)
                for xxx, yyy in self.adj(xx, yy):
                    self.model.addConstr((self.is_cut[x, y][xx, yy, xxx, yyy] == 1) >> (self.ans[xx, yy] + self.ans[xxx, yyy] == 1))

    def rule_no2x2(self, color=1):
        for x in range(self.n - 1):
            for y in range(self.m - 1):
                if color == 0:
                    self.model.addConstr(self.ans[x, y] + self.ans[x + 1, y] + self.ans[x, y + 1] + self.ans[x + 1, y + 1] >= 1)
                else:
                    self.model.addConstr(self.ans[x, y] + self.ans[x + 1, y] + self.ans[x, y + 1] + self.ans[x + 1, y + 1] <= 3)

    def rule_connected(self, color):
        self.add_e(color, 'ans')
        try:
            self.s
        except:
            self.s = {}
            self.t = {}
        self.s[color] = self.model.addVars(self.n, self.m, vtype=GRB.BINARY, name=f's_{color}')
        self.t[color] = self.model.addVars(self.n, self.m, vtype=GRB.BINARY, name=f't_{color}')
        self.model.addConstr(self.s[color].sum() == 1)
        for x in range(self.n):
            for y in range(self.m):
                self.model.addConstr((self.ans[x, y] == 1 - color) >> (self.s[color][x, y] == 0))
                self.model.addConstr((self.ans[x, y] == color) >> (self.t[color][x, y] == 1 - self.s[color][x, y]))
                self.model.addConstr((self.ans[x, y] == 1 - color) >> (self.t[color][x, y] == 0))
        for x in range(self.n):
            for y in range(self.m):
                self.model.addConstr((self.s[color][x, y] == 1) >> (self.sum_out[color][x, y] == self.sum_in[color][x, y] + self.cnt[color] - 1))
                self.model.addConstr((self.t[color][x, y] == 1) >> (self.sum_out[color][x, y] == self.sum_in[color][x, y] - 1))

    def rule_allmarked(self, color):
        for x in range(self.n):
            for y in range(self.m):
                self.model.addConstr((self.ans[x, y] == color) >> (gp.quicksum(self.is_belong[key][x, y] for key in self.is_belong) == 1))

    def solve(self):
        self.model.optimize()


if __name__ == '__main__':
    board = Board(3, 4)
    # board.clue_color(0, 0, 0)
    board.clue_size(0, 0, 6, 0)
    # board.clue_color(2, 0, 0)
    board.clue_color(1, 1, 1)
    board.clue_color(1, 2, 0)
    # board.clue_color(0, 3, 1)
    # board.clue_color(2, 3, 1)
    board.clue_size(2, 3, 6, 1)
    board.rule_connected(0)
    board.rule_connected(1)
    board.solve()
    board.model.write('board.lp')
    try:
        print(np.array([[board.ans[i, j].x for j in range(board.m)] for i in range(board.n)]))
        board.model.write('board.sol')
    except:
        board.model.computeIIS()
        board.model.write('board.ilp')