import gspread
import os
import shutil
import sys

from cogs.exceptions import CogsError, DeleteError
from cogs.helpers import get_client, get_config, validate_cogs_project


def delete():
    """Read COGS configuration and delete the Sheet corresponding to the Google Sheet ID. Remove
    .cogs directory."""
    validate_cogs_project()
    config = get_config()

    resp = input(
        "WARNING: This task will permanently destroy the Google Sheet and all COGS data.\n"
        "         Do you wish to proceed? [y/n]\n"
    )
    if resp.lower().strip() != "y":
        print("'delete' operation stopped")
        sys.exit(0)

    # Get a client to perform Sheet actions
    gc = get_client(config["Credentials"])

    # Delete the Sheet
    title = config["Title"]
    cwd = os.getcwd()
    print(f"Removing COGS project '{title}' from {cwd}")
    try:
        gc.del_spreadsheet(config["Google Sheet ID"])
    except gspread.exceptions.APIError as e:
        raise DeleteError(
            f"ERROR: Unable to delete Sheet '{title}'\n" f"CAUSE: {e.response.text}"
        )

    # Remove the COGS data
    if os.path.exists(".cogs"):
        shutil.rmtree(".cogs")


def run(args):
    """Wrapper for delete function."""
    try:
        delete()
    except CogsError as e:
        print(str(e))
        sys.exit(1)
