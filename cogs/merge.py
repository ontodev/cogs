import csv
import logging
import os
import re
import shutil

from cogs.helpers import (
    get_cached_path,
    get_cached_sheets,
    get_renamed_sheets,
    get_tracked_sheets,
    set_logging,
    validate_cogs_project,
)


def copy_to_csv(cached_sheet, local_sheet):
    """Copy a cached sheet (TSV) to its local CSV path as CSV."""
    with open(local_sheet, "w") as fw:
        writer = csv.writer(fw, lineterminator="\n")
        with open(cached_sheet, "r") as fr:
            writer.writerows(csv.reader(fr, delimiter="\t"))


def merge(verbose=False):
    """Copy cached sheets to their local paths."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()

    cached_sheets = get_cached_sheets(cogs_dir)
    tracked_sheets = get_tracked_sheets(cogs_dir)
    tracked_cached = [re.sub(r"[^A-Za-z0-9]+", "_", x.lower()) for x in tracked_sheets.keys()]
    remove_sheets = [s for s in cached_sheets if s not in tracked_cached]

    # Get the list of ignored sheet titles
    ignore = [x for x, y in tracked_sheets.items() if y.get("Ignore") == "True"]

    for sheet_title, details in tracked_sheets.items():
        if sheet_title in ignore:
            continue
        cached_path = get_cached_path(cogs_dir, sheet_title)
        local_sheet = details["Path"]
        if os.path.exists(cached_path):
            logging.info(f"Writing '{sheet_title}' to {local_sheet}")
            if local_sheet.endswith(".csv"):
                copy_to_csv(cached_path, local_sheet)
            else:
                shutil.copyfile(cached_path, local_sheet)
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
