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


def share(email, role, verbose=False):
    """Share the project spreadsheet with email addresses as reader, writer, or owner."""
    set_logging(verbose)
    validate_cogs_project()

    config = get_config()
    gc = get_client_from_config(config)

    title = config["Title"]
    spreadsheet = gc.open(title)

    if role == "owner":
        share_spreadsheet(title, spreadsheet, email, "owner")
    elif role == "reader":
        share_spreadsheet(title, spreadsheet, email, "reader")
    elif role == "writer":
        share_spreadsheet(title, spreadsheet, email, "writer")
    else:
        raise RuntimeError("Unknown role passed to `share`: " + str(role))


def run(args):
    """Wrapper for share function."""
    try:
        if args.owner:
            transfer = True
            if not args.force:
                resp = input(
                    f"WARNING: Transferring ownership to {args.owner} will prevent COGS from "
                    f"performing admin actions on the Spreadsheet. Do you wish to proceed? [y/n]\n"
                )
                if resp.lower().strip() != "y":
                    print(f"Ownership of Spreadsheet will not be transferred.")
                    transfer = False
            if transfer:
                share(args.owner, "owner", verbose=args.verbose)
        if args.writer:
            share(args.writer, "writer", verbose=args.verbose)
        if args.reader:
            share(args.reader, "reader", verbose=args.verbose)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
