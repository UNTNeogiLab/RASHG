import param


class instruments(param.Parameterized):
    def __init__(self):
        super().__init__()

    def initialize(self):
        pass

    def get_frame(self, o, p):
        pass

    def live(self):
        pass

    def power_step(self):
        pass

    def wav_step(self):
        pass

    def widgets(self):
        pass