import shutil
import sys

from cogs.exceptions import DeleteError
from cogs.helpers import *


def msg():
    return "Delete the Google spreadsheet and COGS configuration"


def delete(verbose=False):
    """Read COGS configuration and delete the spreadsheet corresponding to the spreadsheet ID.
    Remove .cogs directory."""
    set_logging(verbose)
    validate_cogs_project()
    config = get_config()

    # Get a client to perform Sheet actions
    gc = get_client_from_config(config)

    # Delete the Sheet
    title = config["Title"]
    cwd = os.getcwd()
    print(f"Removing COGS project '{title}' from {cwd}")
    try:
        ssid = config["Spreadsheet ID"]
        gc.del_spreadsheet(ssid)
    except gspread.exceptions.APIError as e:
        raise DeleteError(f"Unable to delete spreadsheet '{title}'\n" f"CAUSE: {e.response.text}")
    logging.info(f"successfully deleted Google Sheet '{title}' ({ssid})")

    # Remove the COGS data
    if os.path.exists(".cogs"):
        shutil.rmtree(".cogs")


def run(args):
    """Wrapper for delete function."""
    try:
        if not args.force:
            resp = input(
                "WARNING: This task will permanently destroy the spreadsheet and all COGS data.\n"
                "         Do you wish to proceed? [y/n]\n"
            )
            if resp.lower().strip() != "y":
                logging.warning("'delete' operation stopped")
                sys.exit(0)
        delete(verbose=args.verbose)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
