import csv
import logging
import os
import re
import sys

from cogs.exceptions import CogsError, FetchError
from cogs.helpers import (
    get_config,
    get_client,
    get_fields,
    get_sheets,
    set_logging,
    validate_cogs_project,
)


def get_remote_sheets(sheets):
    """Retrieve a map of sheet title -> sheet ID from the spreadsheet."""
    # Validate sheet titles before downloading anything
    remote_sheets = {}
    for sheet in sheets:
        if sheet.title in ["user", "config", "sheet", "field"]:
            raise FetchError(
                f"cannot export remote sheet with the reserved name '{sheet.title}'"
            )
        remote_sheets[sheet.title] = sheet.id
    return remote_sheets


def fetch(args):
    """Fetch all sheets from project spreadsheet to .cogs/ directory."""
    set_logging(args.verbose)
    validate_cogs_project()

    config = get_config()
    client = get_client(config["Credentials"])
    title = config["Title"]
    spreadsheet = client.open(title)

    # Get existing fields to see if we need to add new fields
    fields = get_fields()
    update_fields = False

    # Get the remote sheets from spreadsheet
    sheets = spreadsheet.worksheets()
    remote_sheets = get_remote_sheets(sheets)

    # Get all cached sheet titles that are not COGS defaults
    cached_sheet_titles = []
    for f in os.listdir(".cogs"):
        if f not in ["user.tsv", "sheet.tsv", "field.tsv", "config.tsv"]:
            cached_sheet_titles.append(f.split(".")[0])

    # Export the sheets as TSV to .cogs/ (while checking the fieldnames)
    for sheet in sheets:
        logging.info(f"Downloading '{sheet.title}'")
        with open(f".cogs/{sheet.title}.tsv", "w") as f:
            lines = sheet.get_all_values()
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerows(lines)

            # Check for new fields in sheet header
            if lines:
                for h in lines[0]:
                    field = re.sub(r"[^A-Za-z0-9]+", "_", h.lower()).strip("_")
                    if field not in fields:
                        update_fields = True
                        fields[field] = {"Label": h, "Datatype": "cogs:text", "Description": ""}

    # Update field.tsv if we need to
    if update_fields:
        with open(".cogs/field.tsv", "w") as f:
            writer = csv.DictWriter(
                f,
                delimiter="\t",
                lineterminator="\n",
                fieldnames=["Field", "Label", "Datatype", "Description"],
            )
            writer.writeheader()
            for field, items in fields.items():
                items["Field"] = field
                writer.writerow(items)

    # Update local sheets with new IDs
    local_sheets = get_sheets()
    all_sheets = []
    for sheet_title, details in local_sheets.items():
        if sheet_title in remote_sheets:
            sid = remote_sheets[sheet_title]
            details["ID"] = sid
        details["Title"] = sheet_title
        all_sheets.append(details)

    # Get just the remote sheets that are not in local sheets
    new_sheets = {
        sheet_title: sid
        for sheet_title, sid in remote_sheets.items()
        if sheet_title not in local_sheets
    }
    for sheet_title, sid in new_sheets.items():
        logging.info(f"new sheet '{sheet_title}' added to project")
        details = {
            "ID": sid,
            "Title": sheet_title,
            "Path": f"{sheet_title}.tsv",
            "Description": "",
        }
        all_sheets.append(details)

    # Then update sheet.tsv
    with open(".cogs/sheet.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["ID", "Title", "Path", "Description"],
        )
        writer.writeheader()
        writer.writerows(all_sheets)


def run(args):
    """Wrapper for fetch function."""
    try:
        fetch(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
