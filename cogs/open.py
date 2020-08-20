import sys

from cogs.helpers import *


def msg():
    return "Display the URL of the spreadsheet"


def openSheet(args):
    """Display the URL of the spreadsheet."""
    set_logging(args.verbose)
    validate_cogs_project()

    config = get_config()

    spreadsheet_id = config["Spreadsheet ID"]
    print(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}")


def run(args):
    """Wrapper for open function."""
    try:
        openSheet(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
