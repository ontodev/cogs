from cogs.helpers import get_tracked_sheets, set_logging, validate_cogs_project


def msg():
    return "Show all tracked sheets"


def ls(verbose=False):
    """Return a list of [sheet, path] pairs."""
    set_logging(verbose)
    validate_cogs_project()

    tracked_sheets = get_tracked_sheets()
    sheet_details = []
    for sheet, details in tracked_sheets.items():
        sheet_details.append([sheet, "(" + details["Path"] + ")"])

    return sheet_details
