class CMWError(Exception):
    """Base exception for CMW API errors."""

class CMWTimeoutError(CMWError):
    """Raised when a CMW operation times out."""

class CMWMeasurementError(CMWError):
    """Raised when a measurement returns an invalid or error state."""
