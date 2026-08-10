"""Rule-Based Adaptive Trust Framework.

The base package stays importable without Flask. Flask-specific objects are
loaded only when requested.
"""

__version__ = "0.1.1"

from .core import CoreConfig, PolicyProfile


def __getattr__(name: str):
    if name == "RATF":
        from .flask_extension import RATF

        return RATF
    raise AttributeError(name)


__all__ = ["CoreConfig", "PolicyProfile", "RATF", "__version__"]
