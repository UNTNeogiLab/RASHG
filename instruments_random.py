from .instruments_base import instruments_base
import numpy as np
import param
import panel as pn

pn.extension()


class instruments(instruments_base):
    x1 = param.Number(default=0)
    x2 = param.Number(default=100)
    y1 = param.Number(default=0)
    y2 = param.Number(default=100)

    def __init__(self):
        super().__init__()

    def initialize(self):
        self.x = self.x2 - self.x1
        self.y = self.y2 - self.y1
        self.initialized = True
        params = ["x1", "x2", "y1", "y2"]
        for param in params:
            self.param[param].constant = True

    def get_frame(self, o, p):
        return np.random.rand(self.x, self.y)

    def live(self):
        return np.zeros((self.x, self.y))

    def widgets(self):
        return self.param
