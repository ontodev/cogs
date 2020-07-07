class CogsError(Exception):
    """Base class for all COGS errors."""


class InitError(CogsError):
    """Used to indicate an error occurred during the init step."""


class DeleteError(CogsError):
    """Used to indicate an error occurred during the delete step."""


class AddError(CogsError):
    """Used to indicate an error occurred during the add step."""


class FetchError(CogsError):
    """Used to indicate an error occurred during the fetch step."""


class DiffError(CogsError):
    """Used to indicate an error occurred during the diff step."""
