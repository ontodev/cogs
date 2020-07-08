import logging
import os
import shutil
import sys

from cogs.exceptions import CogsError
from cogs.helpers import get_sheets, set_logging, validate_cogs_project


def pull(args):
    """Copy cached sheets to their local paths."""
    set_logging(args.verbose)
    validate_cogs_project()

    tracked_sheets = get_sheets()
    for sheet_title, details in tracked_sheets.items():
        cached_sheet = f".cogs/{sheet_title}.tsv"
        local_sheet = details["Path"]
        if os.path.exists(cached_sheet):
            logging.info(f"Writing '{sheet_title}' to {local_sheet}")
            shutil.copyfile(cached_sheet, local_sheet)


def run(args):
    """Wrapper for pull function."""
    try:
        pull(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
