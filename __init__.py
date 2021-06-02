import os
from inspect import isclass
from pkgutil import iter_modules
from pathlib import Path
from importlib import import_module

instruments = {}
package_dir = str(Path(__file__).resolve().parent)
for (_, module_name, _) in iter_modules([package_dir]):
    if str(module_name).__contains__("instruments"):
        sname = module_name.replace("instruments_", "")
        if not str(sname).__contains__("base"):
            try:
                module = import_module(f"{__name__}.{module_name}")
            except ImportError:
                print(f"{sname} import failed")
            else:
                instruments[str(sname)] = module
from . import gui
