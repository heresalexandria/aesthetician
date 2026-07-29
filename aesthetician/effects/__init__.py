"""Effect library. Importing this package registers every effect module."""

import importlib
import pkgutil

from . import audio, video

for _pkg in (video, audio):
    for _m in pkgutil.iter_modules(_pkg.__path__):
        importlib.import_module(f"{_pkg.__name__}.{_m.name}")
