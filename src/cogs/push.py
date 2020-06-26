import csv
import sys

from cogs.exceptions import CogsError
from cogs.helpers import (
    get_client,
    get_colstr,
    get_config,
    get_worksheets,
    validate_cogs_project,
)


def push():
    """Push local tables to the Sheet as worksheets. Only the worksheets in sheet.tsv will be
    pushed. If a worksheet in the Sheet does not exist in the local sheet.tsv, it will be removed
    from the Sheet. Any worksheet in sheet.tsv that does not exist in the Sheet will be created.
    Any worksheet in sheet.tsv that does exist will be updated."""
    validate_cogs_project()
    config = get_config()
    gc = get_client(config["Credentials"])
    sheet = gc.open(config["Title"])

    local_worksheets = get_worksheets()

    # Clear existing worksheets (wait to delete any that were removed)
    # If we delete first, could throw error where we try to delete the last remaining ws
    remote_worksheets = {}
    for ws in sheet.worksheets():
        t_title = ws.title
        remote_worksheets[t_title] = ws
        colstr = get_colstr(ws.col_count)
        sheet.values_clear(f"{t_title}!A1:{colstr}{ws.row_count}")

    # Add new data to the worksheets in the Sheet
    sheet_rows = []
    for ws_title, details in local_worksheets.items():
        ws_path = details["Path"]
        delimiter = "\t"
        if ws_path.endswith(".csv"):
            delimiter = ","
        rows = []
        cols = 0
        with open(ws_path, "r") as f:
            reader = csv.reader(f, delimiter=delimiter)
            for row in reader:
                row_len = len(row)
                if row_len > cols:
                    cols = row_len
                rows.append(row)

        # Create or get the worksheet
        if ws_title not in remote_worksheets:
            print(f"Creating worksheet '{ws_title}'")
            ws = sheet.add_worksheet(ws_title, rows=len(rows), cols=cols)
        else:
            ws = remote_worksheets[ws_title]
        details["Title"] = ws.title
        details["ID"] = ws.id
        sheet_rows.append(details)

        # Add new values to ws from local
        sheet.values_update(
            f"{ws_title}!A1", params={"valueInputOption": "RAW"}, body={"values": rows}
        )

        # Copy this table into COGS data
        with open(f".cogs/{ws_title}.tsv", "w") as f:
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerows(rows)

    for ws_title, ws in remote_worksheets.items():
        if ws_title not in local_worksheets.keys():
            print(f"Removing worksheet '{ws_title}'")
            sheet.del_worksheet(ws)

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
