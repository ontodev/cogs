import logging
import os

from cogs.helpers import get_client, get_json_credentials, set_logging
from cogs.init import write_data


def connect(key_or_url, credentials=None, force=False, verbose=False):
    """Connect an existing Google Spreadsheet to a new COGS project. Return True if project was
    created. Return False if a COGS project already exists in the directory."""
    set_logging(verbose)
    cwd = os.getcwd()
    if os.path.exists(".cogs"):
        # Do not raise CogsError, or else .cogs/ will be deleted
        logging.critical(f"COGS project already exists in {cwd}/.cogs/")
        return False

    # Create a Client to access API
    if credentials:
        # Use a credentials file
        gc = get_client(credentials_path=credentials)
        credentials_obj = get_json_credentials(credentials_path=credentials)
    else:
        # Use environment vars
        gc = get_client()
        credentials_obj = get_json_credentials()

    # Maybe extract the key from a full URL
    if "docs.google.com" in key_or_url:
        if key_or_url.startswith("http://"):
            key_or_url = key_or_url[7:]
        elif key_or_url.startswith("https://"):
            key_or_url = key_or_url[8:]
        key = key_or_url.split("/")[3]
    else:
        key = key_or_url

    if not force:
        # Retrieve the service email to paste in help message
        service_email = credentials_obj["client_email"]
        # URL of the Spreadsheet
        url = f"https://docs.google.com/spreadsheets/d/{key}"
        input(
            f"""
    You must share this sheet to continue:
      1. Open {url}
      2. Share with (as "Editor"): {service_email}
      3. Uncheck "Notify people" and send
    Press ENTER to continue. Press CTRL + C to cancel.
    """
        )

    # Open the newly-shared sheet
    spreadsheet = gc.open_by_key(key)
    title = spreadsheet.title

    # init the COGS directory
    logging.info(f"connecting COGS project {spreadsheet.title} in {cwd}/.cogs/")
    os.mkdir(".cogs")
    write_data(spreadsheet, title, credentials=credentials)
    return True
