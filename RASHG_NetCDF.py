Machine=True
import numpy as np
import netCDF4
#from ipypb import track
if(Machine):
    from instrumental import instrument, u
    from pyvcam import pvc
    from pyvcam.camera import Camera
    import pyvisa
    import nidaqmx
    from nidaqmx.constants import TerminalConfiguration
else:
    print("RUNNING IN MACHINELESS MODE, data is literally random  or zero")
    '''
    Machine=false disables all the libraries I couldn't get working that do the job of actually reading data and focuses on testing live dataset generation.
    '''
from time import sleep
import time
from datetime import datetime
import subprocess
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d
from tqdm.auto import trange
import matplotlib.pyplot as plt
import RASHG_functions as RASHG

#initialize instruments; in current geometry (7/8/2020), A is #bottom, B is top, C is the attenuator
cam, A, B = RASHG.InitializeInstruments()
rbot = A
rtop = B
# atten = C
rm = pyvisa.ResourceManager()
#Pmeter = rm.open_resource('ASRL3::INSTR')
#MaiTai = rm.open_resource('ASRL1::INSTR')
#MaiTai.write("SHUT 0") #close the shutter
#print('Shutter closed')
rbot.move_home()
rtop.move_home()
print('Homing stages')
# atten.move_home()
x1 = 650
x2 = 1350
y1 = 485
y2 = 985
cam.roi = (x1, x2, y1, y2) #x1, x2, y1, y2
xbin = 2
ybin = 2
cam.binning = (xbin, ybin)
if xbin != ybin:
    print('X-bin and Y-bin must be equal, probably')
#set coordinate dimension sizes and additional
#params here
escape_delay = 0
x = (x2 - x1)/xbin
y = (y2 - y1)/ybin
polarization = 180
pow_start = 20
pow_stop = 25
pow_step = 5
power = (pow_stop-pow_start)/(pow_step)
wavstart = 780
wavend = 782
wavstep = 2
wavwait = 5 #value is in seconds
exp_time = 10000

#initialize the data repository
with netCDF4.Dataset('NeogiLab_data.nc', 'w') as data:

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
    #data.date = str(datetime.date.today()) #out of date
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
                              ('x', 'y', 'ori', 'pol', 'pwr', 'wav'))
    #shg = data.createVariable('shg', np.uint16,
    #                          ('x', 'y', 'ori', 'pol', 'pwr', 'wav'),
    #                          zlib=True,
    #                          chunksizes=[x.size,y.size,1,pol.size,1,1])

    #populate coordinate dimensions
    x[:] = np.arange(x.size, dtype=np.uint16)
    y[:] = np.arange(y.size, dtype=np.uint16)
    ori[:] = np.arange(ori.size, dtype=np.uint16)
    pol[:] = np.arange(pol.size, dtype=np.uint16)
    pwr[:] = np.arange(pow_start,pow_stop,pow_step, dtype=np.uint16)
    wav[:] = np.arange(wavstart, wavend, wavstep, dtype=np.uint16)

    #do power dependence stuff
    if(Machine):
        #PC, PCcov, WavPowAng, pc = RASHG.PCFit(calibration_file)

    #main collection loop; parameters should be set here before running the script. Comment out and untab inner loops as needed.
        #atten.move_to(0)
        time.sleep(escape_delay)
        #MaiTai.write("SHUT 1")
        print('Shutter opened')
    else:
        pass
        #print(data.variables)
    for w in trange(wav.size, desc = "wavelength"):
        if(Machine):
            #MaiTai.write(f"WAV {wav[w]}")
            time.sleep(wavwait) #takes value in seconds
        for pw in trange(pwr.size, desc = "power",leave=False):
            #taken from SetPower(); MAGIC NUMBERS BAD
            if (Machine):
                #atten_pos = RASHG.InvSinSqr(pw, *PC[int((wav[w]-780)/2)])
                #atten.move_to(atten_pos, wait=True)
                for o in trange(ori.size,desc="orientation",leave=False):
                    for p in trange(pol.size, desc="polarization", leave=False) :
                        if(Machine):
                            if o == 1:
                                sys_offset = 45
                            else:
                                sys_offset=0
                            pos = p
                            pos_top = pos  + sys_offset
                            pos_bot = pos
                            rtop.move_to(pos_top)
                            rbot.move_to(pos_bot)
                            shg[:,:,o,p,pw,w] = cam.get_frame(exp_time=
                                                                exp_time)
                        else:
                            shg[:,:,o,p,pw,w] = np.zeros((x.size,y.size))
