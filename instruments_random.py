from .instruments_base import instruments as instruments_base
import numpy as np
import param
import panel as pn


class instruments(instruments_base):
    x1 = param.Number(default=0)
    x2 = param.Number(default=100)
    y1 = param.Number(default=0)
    y2 = param.Number(default=100)

    def __init__(self):
        super().__init__()
        print("RUNNING IN MACHINELESS MODE, data is literally random  or zero")

    def initialize(self):
        self.x = self.x2 - self.x1
        self.y = self.y2 - self.y1

    def get_frame(self, o, p):
        return np.random.rand(self.x, self.y)

    def live(self):
        return np.zeros(self.x, self.y)

    def widgets(self):
        return pn.Param(self.param, parameters=['x1','x2','y1','y2'])
