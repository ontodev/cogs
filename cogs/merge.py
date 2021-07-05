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
    update_sheet,
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

    # Get the list of ignored sheet titles
    ignore = [x for x, y in tracked_sheets.items() if y.get("Ignore")]

    renamed_sheets = get_renamed_sheets(cogs_dir)
    renamed_local = {
        old: details for old, details in renamed_sheets.items() if details["where"] == "local"
    }
    renamed_remote = {
        old: details for old, details in renamed_sheets.items() if old not in renamed_local
    }
    # Add new remotes to tracked cached
    for details in renamed_remote.values():
        tracked_cached.append(re.sub(r"[^A-Za-z0-9]+", "_", details["new"].lower()))

    remove_sheets = [s for s in cached_sheets if s not in tracked_cached]

    for sheet_title, details in tracked_sheets.items():
        if sheet_title in ignore or sheet_title in renamed_remote:
            continue
        cached_path = get_cached_path(cogs_dir, sheet_title)
        local_sheet = details["Path"]
        if os.path.exists(cached_path):
            logging.info(f"Writing '{sheet_title}' to {local_sheet}")
            if local_sheet.endswith(".csv"):
                copy_to_csv(cached_path, local_sheet)
            else:
                shutil.copyfile(cached_path, local_sheet)

    # Handle renamed remote files by replacing their cached copies and adding to sheet.tsv
    for old_title, details in renamed_remote.items():
        new_title = details["new"]
        cached_path = get_cached_path(cogs_dir, old_title)
        logging.info(f"Removing '{old_title}' from cached sheets and replacing with '{new_title}'")
        if os.path.exists(cached_path):
            os.remove(cached_path)

        # Write new copy
        local_sheet = details["path"]
        cached_path = get_cached_path(cogs_dir, new_title)
        if os.path.exists(cached_path):
            logging.info(f"Writing '{new_title}' to {local_sheet}")
            if local_sheet.endswith(".csv"):
                copy_to_csv(cached_path, local_sheet)
            else:
                shutil.copyfile(cached_path, local_sheet)

        # Update sheet.tsv
        sheet_details = tracked_sheets[old_title]
        del tracked_sheets[old_title]
        sheet_details["Path"] = local_sheet
        tracked_sheets[new_title] = sheet_details

    for sheet_title in remove_sheets:
        logging.info(f"Removing '{sheet_title}' from cached sheets")
        os.remove(f"{cogs_dir}/tracked/{sheet_title}.tsv")

    with open(f"{cogs_dir}/renamed.tsv", "w") as f:
        for old_title, details in renamed_local.items():
            new_title = details["new"]
            path = details["path"]
            f.write(f"{old_title}\t{new_title}\t{path}\tlocal\n")

    if renamed_remote:
        # We need to update sheet.tsv if anything was renamed remotely
        sheet_details = []
        for title, details in tracked_sheets.items():
            details["Title"] = title
            sheet_details.append(details)
        update_sheet(cogs_dir, sheet_details, [])
