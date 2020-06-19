class CogsError(Exception):
    """Base class for all COGS errors."""


class InitError(CogsError):
    """Used to indicate an error occurred during the init step."""
