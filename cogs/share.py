import gspread.exceptions
import logging

from cogs.helpers import get_client_from_config, get_config, set_logging, validate_cogs_project


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
    cogs_dir = validate_cogs_project()

    config = get_config(cogs_dir)
    gc = get_client_from_config(config)

    spreadsheet = gc.open_by_key(config["Spreadsheet ID"])
    title = spreadsheet.title

    if role == "owner":
        share_spreadsheet(title, spreadsheet, email, "owner")
    elif role == "reader":
        share_spreadsheet(title, spreadsheet, email, "reader")
    elif role == "writer":
        share_spreadsheet(title, spreadsheet, email, "writer")
    else:
        raise RuntimeError("Unknown role passed to `share`: " + str(role))
