import sys

from cogs.helpers import *


def msg():
    return "Display the URL of the spreadsheet"


def get_sheet_url():
    """Return the URL of the spreadsheet."""
    validate_cogs_project()
    config = get_config()

    spreadsheet_id = config["Spreadsheet ID"]
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"


def run(args):
    """Wrapper for open function."""
    try:
        print(get_sheet_url())
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
