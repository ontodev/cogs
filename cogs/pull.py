import logging
import os
import shutil
import sys

from cogs.exceptions import CogsError
from cogs.helpers import get_cached_sheets, get_tracked_sheets, set_logging, validate_cogs_project


def msg():
    return "Copy fetched sheets to their local paths"


def pull(args):
    """Copy cached sheets to their local paths."""
    set_logging(args.verbose)
    validate_cogs_project()

    cached_sheets = get_cached_sheets()
    tracked_sheets = get_tracked_sheets()
    remove_sheets = [s for s in cached_sheets if s not in tracked_sheets.keys()]
    for sheet_title, details in tracked_sheets.items():
        cached_sheet = f".cogs/{sheet_title}.tsv"
        local_sheet = details["Path"]
        if os.path.exists(cached_sheet):
            logging.info(f"Writing '{sheet_title}' to {local_sheet}")
            shutil.copyfile(cached_sheet, local_sheet)
    for sheet_title in remove_sheets:
        logging.info(f"Removing '{sheet_title}' from cached sheets")
        os.remove(f".cogs/{sheet_title}.tsv")


def run(args):
    """Wrapper for pull function."""
    try:
        pull(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
