from instruments_base import instruments as instruments_base
# from instrumental import instrument, u
# from pyvcam import pvc
# from pyvcam.camera import Camera
import pyvisa
import nidaqmx
from nidaqmx.constants import TerminalConfiguration
import RASHG_functions as RASHG
import time


class instruments(instruments_base):
    exp_time = 10000
    escape_delay = 0
    wavwait = 5

    def __init__(self, x1, x2, y1, y2):
        super.__init__()

    def initialize(self):
        self.cam, self.rbot, self.rtop, self.atten = RASHG.InitializeInstruments()
        self.rbot.move_home()
        self.rtop.move_home()
        print('Homing stages')
        self.atten.move_home()
        self.cam.roi = (x1, x2, y1, y2)

    def get_frame(self, o, p):
        if o == 1:
            sys_offset = 45
        else:
            sys_offset = 0
        pos = p
        pos_top = pos + sys_offset
        pos_bot = pos
        self.rtop.move_to(pos_top)
        self.rbot.move_to(pos_bot)
        return self.cam.get_frame(exp_time=self.exp_time)

    def live(self):
        return self.cam.get_frame(exp_time=self.exp_time)

    def wav_step(self):
        time.sleep(self.wavwait)
