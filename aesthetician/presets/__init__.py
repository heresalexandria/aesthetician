"""Preset library. Importing this package registers every preset module."""

import importlib
import pkgutil

for _m in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{_m.name}")


def _apply_keyword_sidecar() -> None:
    """Merge the legacy keyword sidecar into the registered presets.

    Inline `keywords=` on a Preset always wins the ordering; the sidecar's
    words follow, de-duplicated. An id in the sidecar that no preset owns is
    a validation error (scripts/validate_presets.py), not a crash here, so a
    renamed preset cannot take the app down.
    """
    from ..engine.presets import _PRESETS
    from ._keywords import KEYWORDS

    for pid, extra in KEYWORDS.items():
        p = _PRESETS.get(pid)
        if p is None:
            continue
        seen = set(p.keywords)
        merged = list(p.keywords)
        for k in extra:
            if k not in seen:
                seen.add(k)
                merged.append(k)
        p.keywords = tuple(merged)


_apply_keyword_sidecar()
