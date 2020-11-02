import sys

from cogs.helpers import *


def msg():
    return "Share the spreadsheet with a user"


def share_spreadsheet(title, spreadsheet, user, role):
    """Share a sheet with a user (email) as role (reader, writer, owner)"""
    logging.info(f"Sharing spreadsheet '{title}' with {user} as '{role}'")
    try:
        spreadsheet.share(user, perm_type="user", role=role)
    except gspread.exceptions.APIError as e:
        logging.error(f"Unable to share spreadsheet '{title}'\n" + e.response.text)


def share(args):
    """Share the project spreadsheet with email addresses as reader, writer, or owner."""
    set_logging(args.verbose)
    validate_cogs_project()

    config = get_config()
    gc = get_client_from_config(config)

    spreadsheet = gc.open_by_key(config["Spreadsheet ID"])
    title = spreadsheet.title

    if args.owner:
        resp = input(
            f"WARNING: Transferring ownership to {args.owner} will prevent COGS from performing "
            f"administrative actions on spreadsheet '{title}'. Do you wish to proceed? [y/n]\n"
        )
        if resp.lower().strip() == "y":
            share_spreadsheet(title, spreadsheet, args.owner, "owner")
        else:
            print(f"Ownership of spreadsheet '{title}' will not be transferred.")

    if args.reader:
        share_spreadsheet(title, spreadsheet, args.reader, "reader")

    if args.writer:
        share_spreadsheet(title, spreadsheet, args.writer, "writer")


def run(args):
    """Wrapper for share function."""
    try:
        share(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
