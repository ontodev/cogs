import gspread
import os
import shutil
import sys

from cogs.exceptions import DeleteError
from cogs.helpers import get_client, get_config


def delete():
    """Read COGS configuration and delete the Sheet corresponding to the Google Sheet ID. Remove
    .cogs directory."""
    config = get_config()

    # Validate config
    if "Google Sheet ID" not in config:
        raise DeleteError(
            "ERROR: COGS configuration does not contain 'Google Sheet ID'"
        )
    if "Title" not in config:
        raise DeleteError("ERROR: COGS configuration does not contain 'Title'")
    if "Credentials" not in config:
        raise DeleteError("ERROR: COGS configuration does not contain 'Credentials'")

    gc = get_client(config["Credentials"])
    if not gc:
        raise DeleteError

    # Delete the Sheet
    title = config["Title"]
    print(f"Removing COGS project '{title}'")
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
    except DeleteError as e:
        print(str(e))
        sys.exit(1)
