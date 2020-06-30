import csv
import sys

from cogs.exceptions import CogsError
from cogs.helpers import (
    get_client,
    get_colstr,
    get_config,
    get_sheets,
    validate_cogs_project,
)


def push():
    """Push local tables to the spreadsheet as sheets. Only the sheets in sheet.tsv will be
    pushed. If a sheet in the Sheet does not exist in the local sheet.tsv, it will be removed
    from the Sheet. Any sheet in sheet.tsv that does not exist in the Sheet will be created.
    Any sheet in sheet.tsv that does exist will be updated."""
    validate_cogs_project()
    config = get_config()
    gc = get_client(config["Credentials"])
    spreadsheet = gc.open(config["Title"])

    local_sheets = get_sheets()

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
    for sheet_title, details in local_sheets.items():
        sheet_path = details["Path"]
        delimiter = "\t"
        if sheet_path.endswith(".csv"):
            delimiter = ","
        rows = []
        cols = 0
        with open(sheet_path, "r") as f:
            reader = csv.reader(f, delimiter=delimiter)
            for row in reader:
                row_len = len(row)
                if row_len > cols:
                    cols = row_len
                rows.append(row)

        # Create or get the sheet
        if sheet_title not in remote_sheets:
            print(f"Creating sheet '{sheet_title}'")
            sheet = spreadsheet.add_worksheet(sheet_title, rows=len(rows), cols=cols)
        else:
            sheet = remote_sheets[sheet_title]
        details["Title"] = sheet.title
        details["ID"] = sheet.id
        sheet_rows.append(details)

        # Add new values to ws from local
        spreadsheet.values_update(
            f"{sheet_title}!A1", params={"valueInputOption": "RAW"}, body={"values": rows}
        )

        # Copy this table into COGS data
        with open(f".cogs/{sheet_title}.tsv", "w") as f:
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerows(rows)

    for sheet_title, sheet in remote_sheets.items():
        if sheet_title not in local_sheets.keys():
            print(f"Removing sheet '{sheet_title}'")
            spreadsheet.del_worksheet(sheet)

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
        push()
    except CogsError as e:
        print(str(e))
        sys.exit(1)
