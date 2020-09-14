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

    spreadsheet = gc.open_by_key(args.key)
    args.title = spreadsheet.title
    service_email = credentials["client_email"]

    input(
        f"Please go to {spreadsheet.url} and transfer ownership of the sheet to {service_email}: "
        "\n1. Click \"Share\" and share this sheet with the service email"
        "\n2. Click \"Share\" again and click the drop down to the right of the service email"
        "\n3. Select \"Make owner\""
        "\nPress ENTER to continue. Press CTRL + C to cancel."
    )

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
