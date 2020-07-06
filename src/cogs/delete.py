import gspread
import logging
import os
import shutil
import sys

from cogs.exceptions import CogsError, DeleteError
from cogs.helpers import get_client, get_config, set_logging, validate_cogs_project


def delete(args):
    """Read COGS configuration and delete the spreadsheet corresponding to the spreadsheet ID.
    Remove .cogs directory."""
    set_logging(args.verbose)
    validate_cogs_project()
    config = get_config()

    resp = input(
        "WARNING: This task will permanently destroy the spreadsheet and all COGS data.\n"
        "         Do you wish to proceed? [y/n]\n"
    )
    if resp.lower().strip() != "y":
        logging.info("'delete' operation stopped")
        sys.exit(0)

    # Get a client to perform Sheet actions
    gc = get_client(config["Credentials"])

    # Delete the Sheet
    title = config["Title"]
    cwd = os.getcwd()
    print(f"Removing COGS project '{title}' from {cwd}")
    try:
        ssid = config["Spreadsheet ID"]
        gc.del_spreadsheet(ssid)
    except gspread.exceptions.APIError as e:
        raise DeleteError(
            f"Unable to delete spreadsheet '{title}'\n" f"CAUSE: {e.response.text}"
        )
    logging.info(f"successfully deleted Google Sheet '{title}' ({ssid})")

    # Remove the COGS data
    if os.path.exists(".cogs"):
        shutil.rmtree(".cogs")


def run(args):
    """Wrapper for delete function."""
    try:
        delete(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
