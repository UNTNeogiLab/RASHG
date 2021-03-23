
try:
    from . import instruments_random as random
except ImportError:
    print("random import failed")
    random_enabled=False
else:
    random_enabled=True
try:
    from . import instruments_RASHG as RASHG
except ImportError:
    print("RASHG import failed")
    RASHG_enabled = False
else:
    RASHG_enabled=True