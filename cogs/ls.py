import sys
import tabulate

from cogs.helpers import *


def msg():
    return "Show all tracked sheets"


def ls(args):
    """Print a list of tracked files"""
    set_logging(args.verbose)
    validate_cogs_project()

    tracked_sheets = get_tracked_sheets()
    sheet_details = []
    for sheet, details in tracked_sheets.items():
        sheet_details.append([sheet, "(" + details["Path"] + ")"])

    print(tabulate.tabulate(sheet_details, tablefmt="plain"))


def run(args):
    """Wrapper for fetch function."""
    try:
        ls(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
