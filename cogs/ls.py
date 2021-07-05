from cogs.helpers import get_tracked_sheets, set_logging, validate_cogs_project


def ls(verbose=False):
    """Return a list of [sheet, path] pairs."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()

    tracked_sheets = get_tracked_sheets(cogs_dir)
    ignore = [x for x, y in tracked_sheets.items() if y.get("Ignore")]
    sheet_details = [["Tracked:"]]
    for sheet, details in tracked_sheets.items():
        if sheet in ignore:
            continue
        sheet_details.append([" - " + sheet, "(" + details["Path"] + ")"])
    if ignore:
        sheet_details.append([])
        sheet_details.append(["Ignored:"])
        for i in ignore:
            sheet_details.append([" - " + i])

    return sheet_details
