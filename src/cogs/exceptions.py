class CogsError(Exception):
    """Base class for all COGS errors."""


class AddError(CogsError):
    """Used to indicate an error occurred during the add step."""


class DeleteError(CogsError):
    """Used to indicate an error occurred during the delete step."""


class DiffError(CogsError):
    """Used to indicate an error occurred during the diff step."""


class FetchError(CogsError):
    """Used to indicate an error occurred during the fetch step."""


class InitError(CogsError):
    """Used to indicate an error occurred during the init step."""


class RmError(CogsError):
    """Used to indicate an error occurred during the rm step."""
