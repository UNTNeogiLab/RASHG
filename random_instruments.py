import numpy as np
class instruments():
    def __init__(self,x1,x2,y1,y2):
        self.x = x2 - x1
        self.y = y2 - y1
        print("RUNNING IN MACHINELESS MODE, data is literally random  or zero")
    def get_frame(self,o,p):
        return np.random.rand(self.x,self.y)
    def live(self):
        return np.zeros(self.x,self.y)
    def power_step(self):
        pass
    def wav_step(self):
        pass
