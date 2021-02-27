Machine=False 
import panel as pn
from tqdm.notebook import tqdm
import param
import numpy as np
import netCDF4
from time import sleep
from datetime import datetime
import subprocess
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d
from tqdm.auto import trange
import matplotlib.pyplot as plt
import RASHG_functions as RASHG
import xarray as xr
import holoviews as hv
pn.extension('plotly')
hv.extension('bokeh', 'plotly')
if(Machine):
    from instrumental import instrument, u
    from pyvcam import pvc
    from pyvcam.camera import Camera
    import pyvisa
    import nidaqmx
    from nidaqmx.constants import TerminalConfiguration
else:
    print("RUNNING IN MACHINELESS MODE, data is literally random  or zero")
class grapher(param.Parameterized):
    colorMap = param.ObjectSelector(default="fire", objects=hv.plotting.util.list_cmaps())
    cPol = param.Number(default=0)
    filename = "testfile2.nc"
    button = pn.widgets.Button(name='Gather Data', button_type='primary')
    button2 = pn.widgets.Button(name='Live View', button_type='primary')
    live = True
    refresh = 5 #refresh every 5 seconds #make it a parameter
    @param.depends('cPol')
    def progressBar(self):
        return pn.Column(self.pbar,self.wbar,self.obar,self.polbar)
    def __init__(self):
        super().__init__()
        self.pbar = tqdm(desc = "power") #power
        self.wbar = tqdm(desc = "wavelength") #wavelength
        self.obar = tqdm(desc = "orientation") #orientation
        self.polbar = tqdm(desc = "polarization") #polarization
        self.init_vars()
        self.cache = np.random.rand(100,100)
        if(Machine):
            self.init_instruments()
    def init_vars(self):
        if(not Machine):
            self.x1 = 0
            self.x2 = 100
            self.y1 = 0
            self.y2 = 100 #todo make GUI
        escape_delay = 0
        x = self.x2 - self.x1
        y = self.y2 - self.y1
        polarization = 180
        pow_start = 0
        pow_stop = 5
        pow_step = 5
        power = (pow_stop-pow_start)/(pow_step)
        wavstart = 780
        wavend = 800
        wavstep = 2
        self.wavwait = 5 #value is in seconds
        exp_time = 1000
        self.data = netCDF4.Dataset(self.filename, 'w')
        x = self.data.createDimension('x', x)
        y = self.data.createDimension('y', y)
        pol = self.data.createDimension('pol', polarization)
        pwr = self.data.createDimension('pwr', power)
        wav = self.data.createDimension('wav', (wavend-wavstart)/wavstep)
        ori = self.data.createDimension('ori', 2)

        #populate metadata
        self.data.title = 'Power/Wavelength dependent RASHG'
        self.data.institution = 'University of North Texas'
        #data.date = str(datetime.date.today()) #out of date
        self.data.sample = 'MoS2'

        #create variables; in this case, the only dependent variable is 'shg',
        #which is the shg intensity along the specified dimensions
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
        #shg = data.createVariable('shg', np.uint16,
        #                          ('x', 'y', 'ori', 'pol', 'pwr', 'wav'),
        #                          zlib=True, 
        #                          chunksizes=[x.size,y.size,1,pol.size,1,1])

        #populate coordinate dimensions
        self.x[:] = np.arange(self.x.size, dtype=np.uint16)
        self.y[:] = np.arange(self.y.size, dtype=np.uint16)
        self.ori[:] = np.arange(self.ori.size, dtype=np.uint16)
        self.pol[:] = np.arange(self.pol.size, dtype=np.uint16)
        self.pwr[:] = np.arange(pow_start,pow_stop,pow_step, dtype=np.uint16)
        self.wav[:] = np.arange(wavstart, wavend, wavstep, dtype=np.uint16)
        self.cache=np.random.rand(x.size,y.size)
    def init_instruments(self):
        self.cam, A, B, C = RASHG.InitializeInstruments()
        self.rbot = A
        self.rtop = B
        self.atten = C
        rm = pyvisa.ResourceManager()
        self.Pmeter = rm.open_resource('ASRL3::INSTR')
        self.MaiTai = rm.open_resource('ASRL1::INSTR')
        self.MaiTai.write("SHUT 0") #close the shutter
        print('Shutter closed')
        self.rbot.home(wait=False)
        self.rtop.home(wait=False)
        print('Homing stages')
        self.atten.home(wait=True)
        self.cam.roi = (x1, x2, y1, y2) #x1, x2, y1, y2
        PC, PCcov, WavPowAng, pc = RASHG.PCFit(calibration_file)

    #main collection loop; parameters should be set here before running the script. Comment out and untab inner loops as needed.
        atten.move_to(0*u.degree, wait=True)
        time.sleep(escape_delay)
        MaiTai.write("SHUT 1")
        print('Shutter opened')
    def gather_data(self, event = None):
        self.button.disabled = True
        self.live = False
        print("Gathering Data")
        pit = range(self.pwr.size) #power, polarization, wavelength, orientation respectively
        polit = range(self.pol.size)
        wit = range(self.wav.size)
        self.wbar.reset(total=len(wit))
        oit = range(self.ori.size)
        for w in wit:
            if(Machine):
                self.MaiTai.write(f"WAV {wav[w]}")
                time.sleep(self.wavwait) #takes value in seconds
            self.pbar.reset(total=len(pit))
            for pw in pit:
                if (Machine):
                    self.atten_pos = RASHG.InvSinSqr(pw, *PC[int((wav[w]-780)/2)])
                    self.atten.move_to(atten_pos, wait=True)
                self.obar.reset(total=len(oit))
                for o in oit:
                    self.polbar.reset(total=len(polit))
                    for p in polit:
                        self.cPol = p
                        if(Machine):
                            if o == o[1]:
                                sys_offset = 45
                            pos = p * u.degree
                            pos_top = pos - rtop.offset + sys_offset
                            pos_bot = pos - rbot.offset
                            rtop.move_to(pos_top, wait=False)
                            rbot.move_to(pos_bot, wait=True)
                            self.cache = cam.get_frame(exp_time=exp_time)
                            shg[:,:,o,p,pw,w] = self.cache
                        else:
                            self.cache=np.random.rand(self.x.size,self.y.size)
                            self.shg[:,:,o,p,pw,w] = self.cache
                        self.polbar.update()
                    self.obar.update()
                self.pbar.update()
            self.wbar.update()
    def live_view(self, event = None):
        print("Initializing live view") 
        self.button2.disabled = True
        while self.live:
            if(Machine):
                self.cache = cam.get_frame(exp_time=exp_time)
            else:
                self.cache = np.zeros((self.x.size,self.y.size))
            self.cPol = self.cPol + 1
            sleep(self.refresh)
            if not live:
                break
    @param.depends('cPol')
    def graph(self):
        output = self.cache
        print(output)
        self.zdim = hv.Dimension('Intensity', range=(output.min(), output.max()))
        opts = [hv.opts.Image(colorbar=True, cmap=self.colorMap, tools=['hover'], framewise=True, logz=True)]
        return hv.Image(output, vdims=self.zdim).opts(opts).redim(x=self.xDim, y=self.yDim)
        
    def output(self):
        self.button.on_click(self.gather_data)
        self.button2.on_click(self.live_view)
        return pn.Row(self.progressBar, pn.Column(self.button,self.button2),self.param.colorMap, self.graph)

graph = grapher()
graph.output().show()

