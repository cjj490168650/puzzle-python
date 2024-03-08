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
        self.cnt = self.model.addVars(2, vtype=GRB.INTEGER, name='cnt')
        self.model.addConstr(self.cnt[0] == self.n * self.m - self.ans.sum())
        self.model.addConstr(self.cnt[1] == self.ans.sum())
        self.clues = {"color": {}, "size": {}}
        self.add_cut()
        self.add_e()

    def adj(self, x, y):
        res = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            if 0 <= x + dx < self.n and 0 <= y + dy < self.m:
                res.append((x + dx, y + dy))
        return res
    
    def add_cut(self):
        self.is_cut = {}
        for x in range(self.n):
            for y in range(self.m):
                for xx, yy in self.adj(x, y):
                    self.is_cut[x, y, xx, yy] = self.model.addVar(vtype=GRB.BINARY, name=f'is_cut[{x},{y},{xx},{yy}]')
                    self.model.addConstr(self.is_cut[x, y, xx, yy] <= self.ans[x, y] + self.ans[xx, yy])
                    self.model.addConstr(self.is_cut[x, y, xx, yy] <= 2 - self.ans[x, y] - self.ans[xx, yy])
                    self.model.addConstr(self.is_cut[x, y, xx, yy] >= self.ans[x, y] - self.ans[xx, yy])
                    self.model.addConstr(self.is_cut[x, y, xx, yy] >= self.ans[xx, yy] - self.ans[x, y])

    def add_e(self):
        self.e = {}
        self.s = {}
        self.t = {}
        self.sum_in = self.model.addVars(self.n, self.m, vtype=GRB.INTEGER, name=f'sum_in')
        self.sum_out = self.model.addVars(self.n, self.m, vtype=GRB.INTEGER, name=f'sum_out')
        for x in range(self.n):
            for y in range(self.m):
                for xx, yy in self.adj(x, y):
                    self.e[x, y, xx, yy] = self.model.addVar(vtype=GRB.INTEGER, lb=0, name=f'e[{x},{y},{xx},{yy}]')
                    self.model.addConstr((self.is_cut[x, y, xx, yy] == 1) >> (self.e[x, y, xx, yy] == 0))
                    # self.model.addConstr((self.is_cut[x, y, xx, yy] == 0) >> (self.e[x, y, xx, yy] >= 1))
        for x in range(self.n):
            for y in range(self.m):
                self.model.addConstr(self.sum_out[x, y] == gp.quicksum(self.e[x, y, xx, yy] for xx, yy in self.adj(x, y)))
                self.model.addConstr(self.sum_in[x, y] == gp.quicksum(self.e[xx, yy, x, y] for xx, yy in self.adj(x, y)))
    
    def clue_color(self, x, y, color):
        self.clues["color"][x, y] = color
        self.model.addConstr(self.ans[x, y] == color)

    def clue_size(self, x, y, size, color=0):
        self.clues["size"][x, y] = size
        if color != -1:
            self.clue_color(x, y, color)

    def build_size(self):
        keys = list(self.clues["size"].keys())
        self.is_belong = self.model.addVars(self.n, self.m, len(keys) + 1, vtype=GRB.BINARY, name="is_belong")
        self.is_belong_and = {}
        self.s["size"] = self.model.addVars(self.n, self.m, vtype=GRB.BINARY, name="s_size")
        self.t["size"] = self.model.addVars(self.n, self.m, vtype=GRB.BINARY, name="t_size")
        for x in range(self.n):
            for y in range(self.m):
                self.model.addConstr(gp.quicksum(self.is_belong[x, y, i] for i in range(len(keys) + 1)) == 1)
                self.model.addConstr((self.is_belong[x, y, 0] == 1) >> (self.t["size"][x, y] == 0))
                self.model.addConstr((self.is_belong[x, y, 0] == 0) >> (self.t["size"][x, y] == 1 - self.s["size"][x, y]))
                self.model.addConstr((self.t["size"][x, y] == 1) >> (self.sum_out[x, y] == self.sum_in[x, y] - 1))
                if (x, y) in self.clues["size"]:
                    i = list(keys).index((x, y)) + 1
                    self.model.addConstr(self.s["size"][x, y] == 1)
                    self.model.addConstr(self.is_belong[x, y, i] == 1)
                    self.model.addConstr(self.sum_out[x, y] == self.sum_in[x, y] + self.clues["size"][x, y] - 1)
                    self.model.addConstr(gp.quicksum(self.is_belong[xx, yy, i] for xx in range(self.n) for yy in range(self.m)) == self.clues["size"][x, y])
                    for xx in range(self.n):
                        for yy in range(self.m):
                            if abs(x - xx) + abs(y - yy) >= self.clues["size"][x, y]:
                                self.model.addConstr(self.is_belong[xx, yy, i] == 0)
                else:
                    self.model.addConstr(self.s["size"][x, y] == 0)
                for xx, yy in self.adj(x, y):
                    for i in range(len(keys) + 1):
                        self.is_belong_and[x, y, xx, yy, i] = self.model.addVar(vtype=GRB.BINARY, name=f'is_belong_and[{x},{y},{xx},{yy},{i}]')
                        self.model.addConstr(self.is_belong_and[x, y, xx, yy, i] == gp.and_(self.is_belong[x, y, i], self.is_belong[xx, yy, i]))
                    self.model.addConstr(self.is_cut[x, y, xx, yy] == 1 - gp.quicksum(self.is_belong_and[x, y, xx, yy, i] for i in range(len(keys) + 1)))

    def rule_no2x2(self, color=1):
        for x in range(self.n - 1):
            for y in range(self.m - 1):
                if color == 0:
                    self.model.addConstr(self.ans[x, y] + self.ans[x + 1, y] + self.ans[x, y + 1] + self.ans[x + 1, y + 1] >= 1)
                else:
                    self.model.addConstr(self.ans[x, y] + self.ans[x + 1, y] + self.ans[x, y + 1] + self.ans[x + 1, y + 1] <= 3)

    def rule_connected(self, color):
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
                self.model.addConstr((self.s[color][x, y] == 1) >> (self.sum_out[x, y] == self.sum_in[x, y] + self.cnt[color] - 1))
                self.model.addConstr((self.t[color][x, y] == 1) >> (self.sum_out[x, y] == self.sum_in[x, y] - 1))

    def rule_nurikabe(self):
        for x in range(self.n):
            for y in range(self.m):
                self.model.addConstr((self.is_belong[x, y, 0] == 1) >> (self.ans[x, y] == 1))
                self.model.addConstr((self.is_belong[x, y, 0] == 0) >> (self.ans[x, y] == 0))
    
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