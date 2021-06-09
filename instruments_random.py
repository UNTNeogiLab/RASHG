from .instruments_base import instruments_base
import numpy as np
import param
import panel as pn
from numba import njit
import math

pn.extension()


@njit(cache=True)
def zeros(x, y):
    return np.zeros((x, y))


@njit(cache=True)
def random(x, y):
    return np.random.rand(x, y)


class instruments(instruments_base):
    x1 = param.Integer(default=0, bounds=(0, 2047))
    x2 = param.Integer(default=100, bounds=(0, 2047))
    y1 = param.Integer(default=0, bounds=(0, 2047))
    y2 = param.Integer(default=100, bounds=(0, 2047))
    wavstart = param.Integer(default=780)
    wavend = param.Integer(default=800)
    wavstep = param.Integer(default=2)
    ybin = 1
    xbin = 1
    type = "random"
    dimensions = ["wavelength", "power", "Orientation", "Polarization", "x", "y"]

    def __init__(self):
        super().__init__()

    def initialize(self):
        self.x = self.x2 - self.x1
        self.y = self.y2 - self.y1
        self.initialized = True
        params = ["x1", "x2", "y1", "y2"]
        for param in params:
            self.param[param].constant = True
        self.wavelength = np.arange(self.wavstart, self.wavend, self.wavstep, dtype=np.uint16)
        self.pwr = np.arange(self.pow_start, self.pow_stop, self.pow_step, dtype=np.uint16)
        self.x = np.arange(x, dtype=np.uint16)
        self.x_mm = np.arange(x, dtype=np.uint16) * 0.05338  # magic
        self.y = np.arange(y, dtype=np.uint16)
        self.y_mm = np.arange(y, dtype=np.uint16) * 0.05338  # magic
        self.Orientation = np.arange(0, 2)
        self.Polarization = np.arange(0, 360, self.pol_step, dtype=np.uint16)
        self.Polarization_radians = np.arange(0, 360, self.pol_step, dtype=np.uint16) * math.pi / 180
        self.pwr = np.arange(self.pow_start, self.pow_stop, self.pow_step, dtype=np.uint16)
        coords = {
            "wavelength": {"unit": "nanometer", "dimension": "wavelength", "values": self.wavelength},

        }

    def get_frame(self, o, p):
        return random(self.x, self.y)

    def live(self):
        return random(self.x, self.y) * 10

    def widgets(self):
        return self.param
