class CogsError(Exception):
    """Base class for all COGS errors."""


class AddError(CogsError):
    """Used to indicate an error occurred during the add step."""


class ApplyError(CogsError):
    """Used to indicate an error occurred during the apply step."""


class ClearError(CogsError):
    """Used to indicate an error occurred during the clear step."""


class DeleteError(CogsError):
    """Used to indicate an error occurred during the delete step."""


class DiffError(CogsError):
    """Used to indicate an error occurred during the diff step."""


class FetchError(CogsError):
    """Used to indicate an error occurred during the fetch step."""


class InitError(CogsError):
    """Used to indicate an error occurred during the init step."""


class MvError(CogsError):
    """Used to indicate an error occurred during the mv step."""


class RmError(CogsError):
    """Used to indicate an error occurred during the rm step."""
