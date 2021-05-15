from time import sleep
import holoviews as hv
import netCDF4
import numpy as np
import panel as pn
import param
from tqdm.notebook import tqdm

pn.extension('plotly')
hv.extension('bokeh', 'plotly')


class grapher(param.Parameterized):
    colorMap = param.ObjectSelector(default="fire", objects=hv.plotting.util.list_cmaps())
    cPol = param.Integer(default=0, precedence=-1)
    polarization = param.Number(default=180, bounds=(0, 360))
    pow_start = param.Integer(default=0)
    pow_stop = param.Integer(default=5)
    pow_step = param.Integer(default=5)
    wavstart = param.Integer(default=780)
    wavend = param.Integer(default=800)
    wavstep = param.Integer(default=2)
    wavwait = param.Number(default=5)  # value is in seconds
    filename = param.String(default="data/testfile2.nc")
    button = pn.widgets.Button(name='Gather Data', button_type='primary')
    button2 = pn.widgets.Button(name='refresh', button_type='primary')
    live = param.Boolean(default=True, precedence=-1)
    refresh = 5  # refresh every 5 seconds #make it a parameter

    @param.depends('cPol')
    def progressBar(self):
        return pn.Column(self.pbar, self.wbar, self.obar)

    def __init__(self):
        super().__init__()
        self.pbar = tqdm(desc="power")  # power
        self.wbar = tqdm(desc="wavelength")  # wavelength
        self.obar = tqdm(desc="orientation")  # orientation
        self.cache = np.random.rand(100, 100)
        self.button.disabled = True
        self.button2.disabled = True

    def initialize(self, instruments):
        self.instruments = instruments
        self.x1, self.x2, self.y1, self.y2 = self.instruments.x1, self.instruments.x2, self.instruments.y1, self.instruments.y2
        self.init_vars()
        self.button.disabled = False
        self.button2.disabled = False
        self.button.on_click(self.gather_data)
        self.button2.on_click(self.live_view)
        params = ["polarization", "pow_start", "pow_stop", "pow_step", "wavstart", "wavend", "wavstep", "wavwait",
                  "filename"]
        for param in params:
            self.param[param].constant = True

    def init_vars(self):
        x = self.x2 - self.x1
        y = self.y2 - self.y1
        power = (self.pow_stop - self.pow_start) / (self.pow_step)

        self.data = netCDF4.Dataset(self.filename, 'w')
        x = self.data.createDimension('x', x)
        y = self.data.createDimension('y', y)
        pol = self.data.createDimension('pol', self.polarization)
        pwr = self.data.createDimension('pwr', power)
        wav = self.data.createDimension('wav', (self.wavend - self.wavstart) / self.wavstep)
        ori = self.data.createDimension('ori', 2)

        # populate metadata
        self.data.title = 'Power/Wavelength dependent RASHG'
        self.data.institution = 'University of North Texas'
        # data.date = str(datetime.date.today()) #out of date
        self.data.sample = 'MoS2'

        # create variables; in this case, the only dependent variable is 'shg',
        # which is the shg intensity along the specified dimensions
        self.x = self.data.createVariable('x', np.uint16, ('x',), zlib=True)
        self.y = self.data.createVariable('y', np.uint16, ('y',), zlib=True)
        self.pol = self.data.createVariable('pol', np.uint16, ('pol',), zlib=True)
        self.pol.longname = 'Polarization Angle'
        self.pol.units = 'degree'
        self.ori = self.data.createVariable('ori', np.uint16, ('ori',), zlib=True)
        self.ori.longname = 'Output Polarization Orientation'
        self.ori.notes = '0 corresponds to parallel, 1 to perpendicular'
        self.pwr = self.data.createVariable('pwr', np.uint16, ('pwr',), zlib=True)
        self.pwr.longname = 'Laser Power'
        self.pwr.units = 'milliwatt'
        self.wav = self.data.createVariable('wav', np.uint16, ('wav',), zlib=True)
        self.wav.longname = 'Laser Wavelength'
        self.wav.units = 'nanometer'
        self.shg = self.data.createVariable('shg', np.uint16,
                                            ('x', 'y', 'ori', 'pol', 'pwr', 'wav'))
        self.xDim = hv.Dimension('x', unit="micrometers")
        self.yDim = hv.Dimension('y', unit="micrometers")
        # populate coordinate dimensions
        self.x[:] = np.arange(self.x.size, dtype=np.uint16)
        self.y[:] = np.arange(self.y.size, dtype=np.uint16)
        self.ori[:] = np.arange(self.ori.size, dtype=np.uint16)
        self.pol[:] = np.arange(self.pol.size, dtype=np.uint16)
        self.pwr[:] = np.arange(self.pow_start, self.pow_stop, self.pow_step, dtype=np.uint16)
        self.wav[:] = np.arange(self.wavstart, self.wavend, self.wavstep, dtype=np.uint16)
        self.cache = np.random.rand(x.size, y.size)

    def gather_data(self, event=None):
        self.button.disabled = True
        self.button2.disabled = True
        self.live = False
        print("Gathering Data")
        pit = range(self.pwr.size)  # power, polarization, wavelength, orientation respectively
        polit = range(self.pol.size)
        wit = range(self.wav.size)
        self.wbar.reset(total=len(wit))
        oit = range(self.ori.size)
        for w in wit:
            self.instruments.wav_step()
            self.pbar.reset(total=len(pit))
            for pw in pit:
                self.instruments.power_step()
                self.obar.reset(total=len(oit))
                for o in oit:
                    for p in polit:
                        self.cache = self.instruments.get_frame(o, p)
                        self.shg[:, :, o, p, pw, w] = self.cache
                    self.cPol = o
                    self.obar.update()
                self.pbar.update()
            self.wbar.update()
        self.button.disabled = False
        self.button2.disabled = False

    def live_view(self, event=None):
        self.button.disabled = True
        print("Initializing live view")
        self.cache = self.instruments.live()
        self.cPol = self.cPol + 1
        self.button.disabled = False

    @param.depends('cPol')
    def graph(self):
        output = self.cache
        self.zdim = hv.Dimension('Intensity', range=(output.min(), output.max()))
        opts = [hv.opts.Image(colorbar=True, cmap=self.colorMap, tools=['hover'], framewise=True, logz=True)]
        return hv.Image(output, vdims=self.zdim).opts(opts).redim(x=self.xDim, y=self.yDim)

    def widgets(self):
        return pn.Column(self.button, self.button2)

    def output(self):

        return pn.Row(self.progressBar, self.graph)
