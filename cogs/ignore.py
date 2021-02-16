import csv
import logging

from cogs.helpers import get_new_path, get_tracked_sheets, set_logging, validate_cogs_project
from cogs.exceptions import IgnoreError


def ignore(sheet, revert=False, verbose=False):
    set_logging(verbose)
    cogs_dir = validate_cogs_project()
    sheets = get_tracked_sheets(cogs_dir)

    if revert:
        if sheet not in sheets:
            raise IgnoreError(f"'{sheet}' is not a tracked sheet and cannot be reverted")
        ignore_sheet = sheets[sheet]
        if ignore_sheet.get("Ignore", "False") != "True":
            raise IgnoreError(f"'{sheet}' is not an ignored sheet and cannot be reverted")
        del ignore_sheet["Ignore"]
        if not ignore_sheet.get("Path"):
            # Add a path if the sheet does not have one already
            # The user can change this path later
            sheet_path = get_new_path(sheets, sheet)
            logging.info(f"'{sheet}' added to project with local path '{sheet_path}'")
            ignore_sheet["Path"] = sheet_path
        ignore_sheet["Title"] = sheet
    else:
        if sheet in sheets:
            ignore_sheet = sheets[sheet]
            ignore_sheet.update({"Title": sheet, "Ignore": True})
        else:
            ignore_sheet = {"Title": sheet, "Ignore": True}

    # Update sheet.tsv
    with open(f"{cogs_dir}/sheet.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=[
                "ID",
                "Title",
                "Path",
                "Description",
                "Frozen Rows",
                "Frozen Columns",
                "Ignore",
            ],
        )
        writer.writeheader()
        for title, details in sheets.items():
            if title != sheet:
                details["Title"] = title
                writer.writerow(details)
        writer.writerow(ignore_sheet)
