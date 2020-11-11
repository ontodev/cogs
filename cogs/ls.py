from cogs.helpers import get_tracked_sheets, set_logging, validate_cogs_project


def ls(verbose=False):
    """Return a list of [sheet, path] pairs."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()

    tracked_sheets = get_tracked_sheets(cogs_dir)
    sheet_details = []
    for sheet, details in tracked_sheets.items():
        sheet_details.append([sheet, "(" + details["Path"] + ")"])

    return sheet_details
