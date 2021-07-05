import csv
import logging
import ntpath
import os
import re

from cogs.helpers import get_tracked_sheets, set_logging, update_sheet, validate_cogs_project
from cogs.exceptions import AddError
from datetime import datetime


def add(path, title=None, description=None, freeze_row=0, freeze_column=0, verbose=False):
    """Add a table (TSV or CSV) to the COGS project. This updates sheet.tsv."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()
    sheets = get_tracked_sheets(cogs_dir)

    if path in sheets and sheets[path]["Ignore"]:
        # The provided path is just the title of an ignored sheet
        add_ignored(cogs_dir, sheets, path, None, description=description)
        return
    if title in sheets and sheets[title]["Ignore"]:
        # A path to write the ignored sheet was provided
        add_ignored(cogs_dir, sheets, title, path, description=description)
        return

    if not os.path.exists(path):
        # Create an empty file if the file doesn't exist
        f = open(path, "w")
        f.close()

    if not title:
        # Create the sheet title from file basename
        title = ntpath.basename(path).split(".")[0]

    # Make sure we aren't duplicating a table
    local_sheets = get_tracked_sheets(cogs_dir)
    if title in local_sheets:
        raise AddError(f"'{title}' sheet already exists in this project")

    # Make sure we aren't duplicating a path
    local_paths = {x["Path"]: t for t, x in local_sheets.items()}
    if path in local_paths.keys():
        other_title = local_paths[path]
        raise AddError(f"Local table {path} already exists as '{other_title}'")

    # Maybe get a description
    if not description:
        description = ""

    # Finally, add this TSV to sheet.tsv
    with open(f"{cogs_dir}/sheet.tsv", "a") as f:
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
        # ID gets filled in when we add it to the Sheet
        writer.writerow(
            {
                "ID": "",
                "Title": title,
                "Path": path,
                "Description": description,
                "Frozen Rows": freeze_row,
                "Frozen Columns": freeze_column,
                "Ignore": False,
            }
        )

    logging.info(f"{title} successfully added to project")


def add_all(verbose=False):
    set_logging(verbose)
    cogs_dir = validate_cogs_project()

    sheets = get_tracked_sheets(cogs_dir)
    sheet_lines = []
    for sheet_title, details in sheets.items():
        ignored = details.get("Ignore")
        if ignored:
            path = re.sub(r"[^A-Za-z0-9]+", "_", sheet_title.lower()) + ".tsv"
            if os.path.exists(path):
                now = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = re.sub(r"[^A-Za-z0-9]+", "_", sheet_title.lower()) + f"_{now}.tsv"
            details["Path"] = path
            logging.info(
                f"Adding ignored sheet '{sheet_title}' to tracked sheets with path '{path}'"
            )
        del details["Ignore"]

        details["Title"] = sheet_title
        sheet_lines.append(details)

    update_sheet(cogs_dir, sheet_lines, [])


def add_ignored(cogs_dir, sheets, title, path, description=None):
    """Add a table currently tracked in sheet.tsv where Ignore=True."""
    details = sheets[title]
    path = path or details.get("Path")

    details["Ignore"] = False
    if description:
        details["Description"] = description
    if not path:
        # No path provided, create a new one
        path = re.sub(r"[^A-Za-z0-9]+", "_", title.lower()) + ".tsv"
        if os.path.exists(path):
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = re.sub(r"[^A-Za-z0-9]+", "_", title.lower()) + f"_{now}.tsv"
    details["Path"] = path

    sheets[title] = details
    sheet_lines = []
    for s, details in sheets.items():
        details["Title"] = s
        sheet_lines.append(details)

    logging.info(f"Adding '{title}' to tracked sheets with path {path}")
    update_sheet(cogs_dir, sheet_lines, [])
