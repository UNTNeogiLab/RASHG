import holoviews as hv
import xarray as xr
import numpy as np
import panel as pn
import param
from numba import njit
from tqdm.notebook import tqdm
import os
import zarr
import itertools

pn.extension('plotly')
hv.extension('bokeh', 'plotly')
compressor = zarr.Blosc(cname="zstd", clevel=3, shuffle=2)


@njit(cache=True)
def compare(xs, dim_cache):
    for i in range(0,len(xs)):
        if xs[i] > dim_cache[i]:
            return i


class gui(param.Parameterized):
    colorMap = param.ObjectSelector(default="fire", objects=hv.plotting.util.list_cmaps())
    cPol = param.Number(default=0, precedence=-1)

    wavwait = param.Number(default=5)  # value is in seconds
    filename = param.String(default="data/testfolder.zarr")
    title = param.String(default="Power/Wavelength dependent RASHG")
    institution = param.String(default="University of North Texas")
    sample = param.String(default="MoS2")
    GUIupdate = param.Boolean(default=True)
    button = pn.widgets.Button(name='Gather Data', button_type='primary')
    button2 = pn.widgets.Button(name='refresh', button_type='primary')
    live = param.Boolean(default=True, precedence=-1)
    refresh = 5  # refresh every 5 seconds #make it a parameter
    live_refresh = param.Integer(default=5)
    dim_cache = [0, 0, 0, 0]

    @param.depends('cPol')
    def progressBar(self):
        return pn.Column(*self.bars)

    def __init__(self):
        super().__init__()
        self.xDim = hv.Dimension('x', unit="micrometers")
        self.yDim = hv.Dimension('y', unit="micrometers")
        self.cache = np.random.rand(100, 100)
        self.button.disabled = True
        self.button2.disabled = True

    def initialize(self, instruments):
        self.instruments = instruments
        self.init_vars()
        self.button.disabled = False
        self.button.on_click(self.gather_data)
        self.live = True
        pn.state.add_periodic_callback(self.live_view, period=self.live_refresh * 1000)
        exclude = ["cPol", "live"]
        for param in self.param:
            if not param in exclude:
                self.param[param].constant = True

    def init_vars(self):

        # populate metadata
        self.attrs = {
            "title": self.title,
            "institution": self.institution,
            "sample": self.sample,
            "source": self.instruments.type,
        }
        for coord in self.instruments.coords:
            self.attrs[coord] = self.instruments.coords[coord]["unit"]
        print(self.attrs)
        self.bars = [tqdm(desc=self.instruments.coords[coord]["name"]) for coord in self.instruments.loop_coords]
        # data.date = str(datetime.date.today()) #out of date
        # create variables; in this case, the only dependent variable is 'shg',
        # which is the shg intensity along the specified dimensions
        # populate coordinate dimensions

        self.cache = self.instruments.live()
        # self.zeros = np.zeros(
        #    (1, self.pwr.size, self.Orientation.size, self.Polarization.size, self.x.size, self.y.size))

        fname = self.filename
        i = 2
        while os.path.isdir(self.filename):
            self.filename = fname.replace(".zarr", f"{i}.zarr")
            i += 1
            print(f"Zarr store exists, trying {self.filename}")
        try:
            os.mkdir(self.filename)
        except:
            raise Exception("folder to create zarr store does not exist")

    def gather_data(self, event=None):
        self.button.disabled = True
        self.button2.disabled = True
        self.live = False
        # power, polarization, wavelength, orientation respectively
        First = True
        ranges = [self.instruments.coords[coord]["values"] for coord in self.instruments.loop_coords]
        '''
        The infinite loop:
        not because it is an actual infinite loop but because it supports a theoretical infinite number of dimensions
        memory limits nonwithstanding
        '''
        for xs in itertools.product(*ranges):
            dim = self.find_dim(xs)
            print(*xs)
            print(dim)
        self.instruments.start()
        for w in wit:
            coords = {
                "wavelength": (["wavelength"], [w]),
                "power": (["power"], self.pwr),
                "Orientation": (["Orientation"], self.Orientation),
                "Polarization": (["Polarization"], self.Polarization_radians),
                "degrees": (["Polarization"], self.Polarization),
                "x_pxls": (["x"], self.x),
                "x": (["x"], self.x_mm),
                "y_pxls": (["y"], self.y),
                "y": (["y"], self.y_mm),
            }
            dims = ["wavelength", "power", "Orientation", "Polarization", "x", "y"]
            self.instruments.wav_step()
            self.pbar.reset(total=len(pit))
            self.data = xr.Dataset(
                data_vars={"ds1": (dims, self.zeros, self.attrs)},
                coords=coords,
                attrs=self.attrs
            )
            for pw in pit:
                self.instruments.power_step()
                self.obar.reset(total=len(oit))
                for o in oit:
                    self.polbar.reset(total=len(polit))
                    for p in polit:
                        self.cache = self.instruments.get_frame(o, p)
                        mask = {"wavelength": w, "power": pw, "Polarization": p, "Orientation": o}
                        self.data["ds1"].loc[mask] = xr.DataArray(self.cache, dims=["x_pxls", "y_pxls"])
                        if self.GUIupdate and self.instruments.type == "RASHG":
                            self.cPol = p
                            self.polbar.update()
                    if self.GUIupdate:
                        self.cPol = o
                        self.obar.update()
                if self.GUIupdate:
                    self.pbar.update()
            if First:
                self.data.to_zarr(self.filename, encoding={"ds1": {"compressor": compressor}}, consolidated=True)
                First = False
            else:
                self.data.to_zarr(self.filename, append_dim="wavelength")
            if self.GUIupdate:
                self.wbar.update()
        print("Finished")
        self.cPol = self.cPol + 1
        self.data.close()
        quit()

    def find_dim(self, xs):
        typed_a = np.array(xs,dtype=np.float64)
        dim = compare(typed_a, self.dim_cache)
        self.dim_cache = typed_a
        return self.instruments.loop_coords[dim]

    def live_view(self):
        if (self.live):
            print("Updating live view")
            self.cache = self.instruments.live()
            self.cPol = self.cPol + 1

    @param.depends('cPol')
    def graph(self):
        output = self.cache
        self.zdim = hv.Dimension('Intensity', range=(output.min(), output.max()))
        opts = [hv.opts.Image(colorbar=True, cmap=self.colorMap, tools=['hover'], framewise=True, logz=True)]
        return hv.Image(output, vdims=self.zdim).opts(opts).redim(x=self.xDim, y=self.yDim)

    def widgets(self):
        return pn.Column(self.button)

    def output(self):

        return pn.Row(self.progressBar, self.graph)

    def stop(self):
        print("shutting down live view")  # doesn't currently  work
