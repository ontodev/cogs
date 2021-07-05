import logging
import os

from cogs.exceptions import IgnoreError
from cogs.helpers import (
    get_cached_path,
    get_tracked_sheets,
    set_logging,
    update_sheet,
    validate_cogs_project,
)


def ignore(sheet_title, verbose=False):
    """Start ignoring an existing sheet by title. This updates sheet.tsv."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()

    sheets = get_tracked_sheets(cogs_dir)
    sheet_details = sheets.get(sheet_title)
    if not sheet_details:
        raise IgnoreError(f"'{sheet_title}' is not a tracked sheet")
    if sheet_details.get("Ignore"):
        raise IgnoreError(f"'{sheet_title}' is already an ignored sheet")

    logging.info(f"Removing '{sheet_title}' from tracking...")

    # Removed cached copy
    cached_path = get_cached_path(cogs_dir, sheet_title)
    if os.path.exists(cached_path):
        os.remove(cached_path)

    # Update sheet.tsv
    sheet_details["Title"] = sheet_title
    sheet_details["Ignore"] = True
    all_sheets = []
    for st, details in sheets.items():
        if st == sheet_title:
            all_sheets.append(sheet_details)
        else:
            details["Title"] = st
            all_sheets.append(details)
    update_sheet(cogs_dir, all_sheets, [])
