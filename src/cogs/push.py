import csv
import logging
import os
import sys

import cogs.status as status

from cogs.exceptions import CogsError
from cogs.helpers import (
    get_client,
    get_colstr,
    get_config,
    get_diff,
    get_sheets,
    set_logging,
    validate_cogs_project,
)


def push(args):
    """Push local tables to the spreadsheet as sheets. Only the sheets in sheet.tsv will be
    pushed. If a sheet in the Sheet does not exist in the local sheet.tsv, it will be removed
    from the Sheet. Any sheet in sheet.tsv that does not exist in the Sheet will be created.
    Any sheet in sheet.tsv that does exist will be updated."""
    set_logging(args.verbose)
    validate_cogs_project()
    config = get_config()
    gc = get_client(config["Credentials"])
    spreadsheet = gc.open(config["Title"])

    # Get tracked sheets
    tracked_sheets = get_sheets()

    # Clear existing sheets (wait to delete any that were removed)
    # If we delete first, could throw error where we try to delete the last remaining ws
    remote_sheets = {}
    for sheet in spreadsheet.worksheets():
        sheet_title = sheet.title
        remote_sheets[sheet_title] = sheet
        colstr = get_colstr(sheet.col_count)
        spreadsheet.values_clear(f"{sheet_title}!A1:{colstr}{sheet.row_count}")

    # Add new data to the sheets in the Sheet
    sheet_rows = []
    for sheet_title, details in tracked_sheets.items():
        sheet_path = details["Path"]
        delimiter = "\t"
        if sheet_path.endswith(".csv"):
            delimiter = ","
        rows = []
        cols = 0
        if not os.path.exists(sheet_path):
            logging.warning(f"'{sheet_title}' exists remotely but has not been pulled")
            continue
        with open(sheet_path, "r") as f:
            reader = csv.reader(f, delimiter=delimiter)
            for row in reader:
                row_len = len(row)
                if row_len > cols:
                    cols = row_len
                rows.append(row)

        # Set sheet size
        if len(rows) < 500:
            y_size = 500
        else:
            y_size = len(rows) + 10
        if cols < 20:
            x_size = 20
        else:
            x_size = cols + 1

        # Create or get the sheet
        if sheet_title not in remote_sheets:
            logging.info(f"creating sheet '{sheet_title}'")
            sheet = spreadsheet.add_worksheet(sheet_title, rows=y_size, cols=x_size)
        else:
            sheet = remote_sheets[sheet_title]
        details["Title"] = sheet.title
        details["ID"] = sheet.id
        sheet_rows.append(details)

        # Add new values to ws from local
        spreadsheet.values_update(
            f"{sheet_title}!A1",
            params={"valueInputOption": "RAW"},
            body={"values": rows},
        )

        # Copy this table into COGS data
        with open(f".cogs/{sheet_title}.tsv", "w") as f:
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerows(rows)

    for sheet_title, sheet in remote_sheets.items():
        if sheet_title not in tracked_sheets.keys():
            logging.info(f"removing sheet '{sheet_title}'")
            # Remove remote copy
            spreadsheet.del_worksheet(sheet)
            # Remove local copy
            if os.path.exists(f".cogs/{sheet_title}.tsv"):
                os.remove(f".cogs/{sheet_title}.tsv")

    with open(".cogs/sheet.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["ID", "Title", "Path", "Description"],
        )
        writer.writeheader()
        writer.writerows(sheet_rows)


def run(args):
    """Wrapper for push function."""
    try:
        push(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
