import sys

from cogs.helpers import *
from cogs.init import write_data


def msg():
    return "Initialize a new COGS project by connecting an existing Google Sheet"


def connect(args):
    """Connect an existing Google Spreadsheet to a new COGS project."""
    set_logging(args.verbose)
    cwd = os.getcwd()
    if os.path.exists(".cogs"):
        # Do not raise CogsError, or else .cogs/ will be deleted
        logging.critical(f"COGS project already exists in {cwd}/.cogs/")
        sys.exit(1)

    # Create a Client to access API
    if args.credentials:
        # Use a credentials file
        gc = get_client(credentials_path=args.credentials)
        credentials = get_credentials(credentials_path=args.credentials)
    else:
        # Use environment vars
        gc = get_client()
        credentials = get_credentials()
    service_email = credentials["client_email"]

    # Maybe extract the key from a full URL
    key_or_url = args.key
    if "docs.google.com" in key_or_url:
        if key_or_url.startswith("http://"):
            key_or_url = key_or_url[7:]
        elif key_or_url.startswith("https://"):
            key_or_url = key_or_url[8:]
        key = key_or_url.split("/")[3]
    else:
        key = key_or_url

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
    args.title = spreadsheet.title

    # init the COGS directory
    logging.info(f"connecting COGS project {spreadsheet.title} in {cwd}/.cogs/")
    os.mkdir(".cogs")
    write_data(args, spreadsheet)


def run(args):
    """Wrapper for connect function."""
    try:
        connect(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
