import sys
import tabulate

from cogs.helpers import *


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


def run(args):
    """Wrapper for ls function."""
    try:
        sheet_details = ls(verbose=args.verbose)
        print(tabulate.tabulate(sheet_details, tablefmt="plain"))
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
