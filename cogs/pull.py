import logging
import os
import re
import shutil

from cogs.helpers import (
    get_cached_sheets,
    get_renamed_sheets,
    get_tracked_sheets,
    set_logging,
    validate_cogs_project,
)


def pull(verbose=False):
    """Copy cached sheets to their local paths."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()

    cached_sheets = get_cached_sheets(cogs_dir)
    tracked_sheets = get_tracked_sheets(cogs_dir)
    tracked_cached = [re.sub(r"[^A-Za-z0-9]+", "_", x.lower()) for x in tracked_sheets.keys()]
    remove_sheets = [s for s in cached_sheets if s not in tracked_cached]

    for sheet_title, details in tracked_sheets.items():
        path_name = re.sub(r"[^A-Za-z0-9]+", "_", sheet_title.lower())
        cached_sheet = f"{cogs_dir}/tracked/{path_name}.tsv"
        local_sheet = details["Path"]
        if os.path.exists(cached_sheet):
            logging.info(f"Writing '{sheet_title}' to {local_sheet}")
            shutil.copyfile(cached_sheet, local_sheet)
    for sheet_title in remove_sheets:
        logging.info(f"Removing '{sheet_title}' from cached sheets")
        os.remove(f"{cogs_dir}/tracked/{sheet_title}.tsv")

    renamed_sheets = get_renamed_sheets(cogs_dir)
    renamed_local = {
        old: details for old, details in renamed_sheets.items() if details["where"] == "local"
    }
    with open(f"{cogs_dir}/renamed.tsv", "w") as f:
        for old_title, details in renamed_local.items():
            new_title = details["new"]
            path = details["path"]
            f.write(f"{old_title}\t{new_title}\t{path}\tlocal\n")
