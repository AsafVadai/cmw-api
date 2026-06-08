# Rohde & Schwarz CMW Series — Python SCPI API
import logging

from .cmw import CMW
from .exceptions import CMWError, CMWTimeoutError, CMWMeasurementError

__version__ = "0.3.0"

__all__ = [
    "CMW",
    "CMWError",
    "CMWTimeoutError",
    "CMWMeasurementError",
    "enable_debug_logging",
]


def enable_debug_logging(level: int = logging.DEBUG, stream=None) -> None:
    """
    Turn on console logging of every SCPI command and response.

    Invaluable for diagnosing connection or measurement issues — every
    ``>>`` (write) and ``<<`` (response) is printed.

    Example
    -------
        import cmw_api
        cmw_api.enable_debug_logging()
        with cmw_api.CMW.via_tcp("192.168.0.1") as cmw:
            cmw.initialize()
    """
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(message)s"))
    scpi_logger = logging.getLogger("cmw_api")
    scpi_logger.addHandler(handler)
    scpi_logger.setLevel(level)
