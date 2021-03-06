import numpy as np
from netCDF4 import Dataset
from ipypb import track
from instrumental import instrument, u
from pyvcam import pvc
from pyvcam.camera import Camera
import pyvisa
from time import sleep
from datetime import datetime
import subprocess
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d
import nidaqmx
from nidaqmx.constants import TerminalConfiguration
import matplotlib.pyplot as plt
import RASHG_functions as RASHG

#initialize instruments; in current geometry (7/8/2020), A is #bottom, B is top, C is the attenuator
cam, A, B, C = RASHG.InitializeInstruments()
rbot = A
rtop = B
atten = C
rm = pyvisa.ResourceManager()
Pmeter = rm.open_resource('ASRL3::INSTR')
MaiTai = rm.open_resource('ASRL1::INSTR')
MaiTai.write("SHUT 0") #close the shutter
print('Shutter closed')
rbot.home(wait=False)
rtop.home(wait=False)
print('Homing stages')
atten.home(wait=True)
cam.roi = (x1, x2, y1, y2) #x1, x2, y1, y2

#set coordinate dimension sizes and additional
#params here
escape_delay = 0
x = x2 - x1
y = y2 - y1
polarization = 180
pow_start = 0
pow_stop = 20
pow_step = 5
wavstart = 780
wavend = 900
wavstep = 2
wavwait = 5 #value is in seconds
exp_time = 1000

#initialize the data repository
with Dataset('NeogiLab_data.nc', 'w', format="NETCDF4") as data:

    #create the dimensions
    x = data.createDimension('x', x)
    y = data.createDimension('y', y)
    pol = data.createDimension('pol', polarization)
    pwr = data.createDimension('pwr', power)
    wav = data.createDimension('wav', (wavend-wavstart)/wavstep)
    ori = data.createDimension('ori', 2)

    #populate metadata
    data.title = 'Power/Wavelength dependent RASHG'
    data.institution = 'University of North Texas'
    data.date = str(datetime.date.today())
    data.sample = 'MoS2'

    #create variables; in this case, the only dependent variable is 'shg',
    #which is the shg intensity along the specified dimensions
    x = data.createVariable('x', np.uint16, ('x',), zlib=True)
    y = data.createVariable('y', np.uint16, ('y',), zlib=True)
    pol = data.createVariable('pol', np.uint16, ('pol',), zlib=True)
    pol.longname = 'Polarization Angle'
    pol.units = 'degree'
    ori = data.createVariable('ori', np.uint16, ('ori',), zlib=True)
    ori.longname = 'Output Polarization Orientation'
    ori.notes = '0 corresponds to parallel, 1 to perpendicular'
    pwr = data.createVariable('pwr', np.uint16, ('pwr',), zlib=True)
    pwr.longname = 'Laser Power'
    pwr.units = 'milliwatt'
    wav = data.createVariable('wav', np.uint16, ('wav',), zlib=True)
    wav.longname = 'Laser Wavelength'
    wav.units = 'nanometer'
    shg = data.createVariable('shg', np.uint16,
                              ('x', 'y', 'ori', 'pol', 'pwr', 'wav'),
                              zlib=True, 
                              chunksizes=[x.size,y.size,1,pol.size,1,1])

    #populate coordinate dimensions
    x[:] = np.arange(x.size, dtype=np.uint16)
    y[:] = np.arange(y.size, dtype=np.uint16)
    ori[:] = np.arange(ori.size, dtype=np.uint16)
    pol[:] = np.arange(pol.size, dtype=np.uint16)
    pwr[:] = np.arange(powstart, dtype=np.uint16)
    wav[:] = np.arange(wavstart, wavend, wavstep, dtype=np.uint16)

    #do power dependence stuff
    PC, PCcov, WavPowAng, pc = RASHG.PCFit(calibration_file)

    #main collection loop; parameters should be set here before running the script. Comment out and untab inner loops as needed.
    atten.move_to(0*u.degree, wait=True)
    time.sleep(escape_delay)
    MaiTai.write("SHUT 1")
    print('Shutter opened')

    for w in tqdm(range(wav.size)):
        MaiTai.write(f"WAV {wav[w]})
        time.sleep(wavwait) #takes value in seconds
        for pw in pwr:
            #taken from SetPower(); MAGIC NUMBERS BAD
            atten_pos = RASHG.InvSinSqr(pw, *PC[int((wav[w]-780)/2)])
            atten.move_to(atten_pos, wait=True)
            for o in ori:
                for p in pol:
                    if o == o[1]:
                        sys_offset = 45
                    pos = p * u.degree
                    pos_top = pos - rtop.offset + sys_offset
                    pos_bot = pos - rbot.offset
                    rtop.move_to(pos_top, wait=False)
                    rbot.move_to(pos_bot, wait=True)
                    shg[:,:,o,p,pw,w] = cam.get_frame(exp_time=
                                                     exp_time)