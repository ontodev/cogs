import gspread
import sys

from cogs.exceptions import CogsError
from cogs.helpers import get_client, get_config, validate_cogs_project


def openSheet(args):
    """Display the URL of the spreadsheet."""
    validate_cogs_project()

    config = get_config()

    spreadsheet_id = config["Spreadsheet ID"]
    print(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}")


def run(args):
    """Wrapper for open function."""
    try:
        openSheet(args)
    except CogsError as e:
        print(str(e))
        sys.exit(1)
