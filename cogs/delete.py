import gspread
import logging
import os
import shutil

from cogs.exceptions import DeleteError
from cogs.helpers import get_client_from_config, get_config, set_logging, validate_cogs_project


def delete(verbose=False):
    """Read COGS configuration and delete the spreadsheet corresponding to the spreadsheet ID.
    Remove .cogs directory."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()
    config = get_config(cogs_dir)

    # Get a client to perform Sheet actions
    gc = get_client_from_config(config)

    # Delete the Sheet
    title = config["Title"]
    cwd = os.getcwd()
    logging.info(f"Removing COGS project '{title}' from {cwd}")
    try:
        ssid = config["Spreadsheet ID"]
        gc.del_spreadsheet(ssid)
    except gspread.exceptions.APIError as e:
        raise DeleteError(f"Unable to delete spreadsheet '{title}'\n" f"CAUSE: {e.response.text}")
    logging.info(f"successfully deleted Google Sheet '{title}' ({ssid})")

    # Remove the COGS data
    if os.path.exists(cogs_dir):
        shutil.rmtree(cogs_dir)
