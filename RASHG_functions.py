from pyvcam import pvc
from pyvcam.camera import Camera
import K10CR1
import nidaqmx
from nidaqmx.constants import TerminalConfiguration
import thorpy as apt
import numpy as np
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d
def InitializeInstruments():
    """
    Initializes the camera and rotators to the desired names.
    TODO: Figure out how to set the camera to 'quantview' mode.

    Parameters
    ----------
    none

    Returns
    -------
    cam : object
        Named pyvcam camera object.
    A : object
        Named Instrumental instrument object.
    B : object
        Named Instrumental instrument object.
    C : object
        Named Instrumental instrument object.

    """

    pvc.init_pvcam()  # Initialize PVCAM
    try:
        cam = next(Camera.detect_camera())  # Use generator to find first camera
        cam.open()  # Open the camera.
        if cam.is_open:
            print("Camera open")
    except:
        print("Error: camera not found")
    l = apt.list_available_devices()
    L = [A, B, C] = [apt.Motor(i[1]) for i in l]
    for i in L:
        i.set_move_home_parameters(2, 1, 10, 0)
        i.set_velocity_parameters(0, 10, 10)
        i.move_home()

    return cam, A, B, C


def CloseInstruments(cam, A, B, C):
    cam.close()
    pvc.uninit_pvcam()


def CheckRotators(A, B, C):
    """
    Verifies physical position of half wave plate rotation mounts and assigns
    initialized rotators to the correct variables for HalfWaveLoop().

    Parameters
    ----------
    A : object
        K10CR1 APT object.
    B : object
        K10CR1 APT object.
    C : object
        K10CR1 APT object.

    Returns
    -------
    rotator_top : object
        Instrumental K10CR1 object.
    rotator_bottom : object
        Instrumental K10CR1 object.
    cp_post : object
        Instrumental K10CR1 object.

    """
    response = ''
    while response != 'y':
        response = input("Are the rotator locations unchanged? Enter " +
                         "'y' to continue, 'n' to manually set rotator_top " +
                         "and rotator_bottom\n" +
                         '>>>')
        rotator_top = input("Enter name (A, B, or C) of post-sample half-wave"
                            + " rotator:\n" +
                            ">>>")
        if rotator_top == 'A':
            rotator_top = A
        elif rotator_top == 'B':
            rotator_top = B
        elif rotator_top == 'C':
            rotator_top = C
        else:
            pass
        rotator_bottom = input("Enter name (A, B, or C) of pre-sample " +
                               "half-wave rotator:\n" +
                               ">>>")
        if rotator_bottom == 'A':
            rotator_bottom = A
        elif rotator_bottom == 'B':
            rotator_bottom = B
        elif rotator_bottom == 'C':
            rotator_bottom = C
        else:
            pass
        cp_post = input("Enter name (A, B, or C) of post-sample " +
                        "quarter-wave rotator:\n" +
                        ">>>")
        if cp_post == 'A':
            cp_post = A
        elif cp_post == 'B':
            cp_post = B
        elif cp_post == 'C':
            cp_post = C
        else:
            pass
    return rotator_top, rotator_bottom, cp_post


def Power():
    """Reads power from Gentec TPM300 via VISA commands
    The while loop avoids outputting invalid token
    >>>returns float

    to-do: incorporate different power ranges (itteratively check all avaliable
    ranges and chose the best fit. Log this choice)"""

    while True:
        try:
            Pread = Pmeter.query("*READPOWER:")
            Power = float(Pread.split('e')[0].split('+')[1])
            return Power
        except:
            continue


def PD():
    with nidaqmx.Task() as task:
        ai_channel = task.ai_channels.add_ai_voltage_chan("Dev1/ai0", terminal_config=TerminalConfiguration.RSE)
        r = task.read(number_of_samples_per_channel=100)
        m = np.mean(r)
        delta = np.std(r)
        return m, delta


# begun 7/8/2020. Finish later.
# class MaiTai:
#    """Class for controlling the MaiTai Ti:Sapphire tunable pulsed
# laser."""
#    def __init__(self, rm):
#        """Sets the serial address for the instrument. Will need to be
#        checked should we move labs. rm is the PyVisa resource manager.
#        """
#        self.address = 'ASRL3::INSTR'
#        self = rm.open_resource(self.address)
#
#    def Shutter(x):
#        if x == 1:
#            MaiT

def MoveWav(position):
    """Helper function for instrumental to avoid clutter and make code
    more readable
    >>>returns null"""
    MaiTai.write(f"WAV {position}")


def ReadWav():
    """Helper function for instrumental to avoid clutter and make code
    more readable
    >>>returns int"""
    w = int(MaiTai.query("WAV?").split('n')[0])
    return w


def Shutter(op):
    """Helper function for instrumental to avoid clutter and make code
    more readable
    >>>returns string"""
    if op == 1:
        MaiTai.write("SHUT 1")
        # tqdm.write("Shutter Opened")
    else:
        MaiTai.write("SHUT 0")
        # tqdm.write("Shutter Closed")


'''def MoveRot(position, Rot=C):
    """Helper function for instrumental to avoid clutter and make code
    more readable
    >>>returns null"""
    Rot.move_to(position*u.degree)
'''  # weird bud C is not defined


def Sin2(angle, mag, xoffset, yoffset):
    return mag * np.sin(angle * 2 * np.pi / 360 - xoffset) ** 2 + yoffset


def PowerFit(datax, datay):
    popt, pcov = curve_fit(Sin2, datax, datay, p0=[1, 1, 1], bounds=([0, 0, 0], [1000, 10, 10]))
    return popt, pcov


def InvSinSqr(y, mag, xoffset, yoffset):
    return np.mod((360 / (2 * np.pi)) * (np.arcsin(np.sqrt(np.abs((y - yoffset) / mag))) + xoffset), 180)


def PCFit(file):
    pc = np.load(file, allow_pickle=True)
    wavelengths = pc[:, 0]
    PC = []
    PCcov = []
    Angles = []
    xx = np.arange(2, 21, 1)
    XX = np.linspace(0, 30, 100)

    for i in range(0, len(pc), 1):
        params, cov = PowerFit(pc[i, 1][0], pc[i, 1][1])
        PC.append(params)
        PCcov.append(cov)
        analyticsin = InvSinSqr(XX, *params)
        interpangles = interp1d(XX, analyticsin)
        angles = interpangles(xx)
        Angs = dict(zip(xx, angles))
        Angles.append(Angs)
    PC = np.asarray(PC)
    PCcov = np.asarray(PCcov)
    # Angles = np.asarray(Angles)
    WavPowAng = dict(zip(wavelengths, Angles))

    return PC, PCcov, WavPowAng, pc


def V2P(wavelength, voltage, pc):
    def Line(x, m, b):
        return m * x + b

    def FitV2P(x, y):
        fit, fitcov = curve_fit(Line, x, y)
        return fit, fitcov

    F = []
    Fcov = []
    for i in range(0, len(pc), 1):
        f, fcov = FitV2P(pc[i, 1][1], pc[i, 1][3])
        F.append(f)
        Fcov.append(fcov)
    F = np.asarray(F)
    M = F[:, 0]
    B = F[:, 1]
    mW = (voltage - B[int((wavelength - 780) / 2)]) / M[int((wavelength - 780) / 2)]
    return mW


def SetPower(power, wavelength, wavelength_start_calib, wavelength_step_calib, PC):
    MoveRot(InvSinSqr(power, *PC[int((wavelength - wavelength_start_calib) / wavelength_step_calib)]))


def LiveCam(cam, exptime, itter):
    import matplotlib.pyplot as plt
    plt.ion()
    i = 1
    cam.start_live(exp_time=exptime)
    im = plt.imshow(cam.get_live_frame())
    while i < itter:
        im.set_data(cam.get_live_frame())
        i = i + 1
        plt.pause(.01)
    cam.stop_live()
