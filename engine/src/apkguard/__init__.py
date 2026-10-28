"""APKGuard analysis engine."""

from ._build import BUILD

__version__ = "0.1.0"


def version_info() -> dict[str, str]:
    return {"version": __version__, "build": BUILD}
