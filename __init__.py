instruments = {}
try:
    from . import instruments_random as random
except ImportError:
    print("random import failed")
else:
    instruments["random"] = random
try:
    from . import instruments_RASHG as RASHG
except ImportError:
    print("RASHG import failed")
else:
    instruments["RASHG"] = RASHG
try:
    from . import instruments_scanimage
except ImportError:
    print("scanimage import failed")
else:
    instruments["scanimage"] = instruments_scanimage
from . import gui
