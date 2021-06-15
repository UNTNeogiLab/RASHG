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
from tqdm.contrib.itertools import product

pn.extension('plotly')
hv.extension('bokeh', 'plotly')
compressor = zarr.Blosc(cname="zstd", clevel=3, shuffle=2)


@njit(cache=True)
def compare(xs, dim_cache):
    for i in range(0, len(xs)):
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
    dim_cache = np.array([0, 0, 0, 0])

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
        self.coords = {}
        for coord in self.instruments.coords:
            values = self.instruments.coords[coord]
            self.attrs[coord] = values["unit"]
            self.coords[coord] = ([values["dimension"]], values["values"])
        print(self.attrs)
        self.bars = [tqdm(desc=self.instruments.coords[coord]["name"]) for coord in self.instruments.loop_coords]
        # data.date = str(datetime.date.today()) #out of date
        # create variables; in this case, the only dependent variable is 'shg',
        # which is the shg intensity along the specified dimensions
        # populate coordinate dimensions

        self.cache = self.instruments.live()
        zero_array = [self.instruments.coords[coord]["values"].size for coord in self.instruments.dimensions]
        zero_array[0] = 1
        self.zeros = xr.DataArray(np.zeros(zero_array), dims=self.instruments.dimensions)
        # Get filename
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
        self.mask = {}
        First = 0
        ranges = [self.instruments.coords[coord]["values"] for coord in self.instruments.loop_coords]
        self.instruments.start()
        '''
        The infinite loop:
        not because it is an actual infinite loop but because it supports a theoretical infinite number of dimensions
        memory limits nonwithstanding
        The generator should be lazy and not overflow your memory. Theoretically.
        '''
        i = 0
        for dim in self.instruments.loop_coords:
            self.bars[i].reset(total=len(self.instruments.coords[dim]["values"]))
            self.mask[dim] = min(self.instruments.coords[dim]["values"])
            i += 1
        print(self.zeros)
        for xs in product(*ranges):
            dim, dim_num = self.find_dim(xs)
            if dim_num == 0:
                if First == 0:
                    First = 1
                elif First == 1:
                    self.data.to_zarr(self.filename, encoding={"ds1": {"compressor": compressor}}, consolidated=True)
                    First += 1
                else:
                    self.data.to_zarr(self.filename, append_dim=self.instruments.loop_coords[0])
                self.coords[self.instruments.loop_coords[0]] = ([dim], [xs[0]])  # update 1st coord after saving
            self.data = xr.Dataset(
                data_vars={"ds1": (self.instruments.dimensions, self.zeros, self.attrs)},
                coords=self.coords,
                attrs=self.attrs
            )
            self.mask[dim] = xs[dim_num]
            function = self.instruments.coords[dim]["function"]
            if not function == "none":
                function(xs)
            if not dim_num == len(xs) - 1:  # reset for all but the last dimension
                self.bars[dim_num + 1].reset()
            else:
                self.cache = self.instruments.get_frame(xs)
                self.data["ds1"].loc[self.mask] = xr.DataArray(self.cache, dims=self.instruments.cap_coords)
            if self.GUIupdate:
                self.cPol += 1  # refresh the GUI
            if not (dim_num == 0 and First == 1):
                self.bars[dim_num].update()  # don't update the first run ever
        self.data.to_zarr(self.filename, append_dim=self.instruments.loop_coords[0])
        self.bars[0].update()
        print("Finished")
        self.cPol = self.cPol + 1
        self.data.close()
        quit()

    def find_dim(self, xs):
        typed_a = np.array(xs, dtype=np.float64)
        dim = compare(typed_a, self.dim_cache)
        self.dim_cache = typed_a
        return self.instruments.loop_coords[dim], dim

    def live_view(self):
        if self.live:
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
