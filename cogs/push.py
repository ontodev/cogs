import gspread.exceptions
import gspread.utils
import gspread_formatting as gf
import sys

from cogs.helpers import *


def msg():
    return "Push local sheets to the spreadsheet"


def add_notes(spreadsheet, sheet_notes, tracked_sheets):
    """Batch add notes to a spreadsheet."""
    requests = []
    for sheet_title, cell_to_note in sheet_notes.items():
        sheet_id = tracked_sheets[sheet_title]["ID"]
        for cell, note in cell_to_note.items():
            row, col = gspread.utils.a1_to_rowcol(cell)
            requests.append({
                    "updateCells": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": row - 1,
                            "endRowIndex": row,
                            "startColumnIndex": col - 1,
                            "endColumnIndex": col,
                        },
                        "rows": [{"values": [{"note": note}]}],
                        "fields": "note",
                    }
                })
    if not requests:
        return
    try:
        logging.info(f"adding {len(requests)} notes to spreadsheet")
        spreadsheet.batch_update({"requests": requests})
    except gspread.exceptions.APIError as e:
        logging.error(
            f"Unable to add {len(requests)} notes to spreadsheet\n"
            + e.response.text
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
    tracked_sheets = get_tracked_sheets()
    renamed_local = get_renamed_sheets()

    # Clear existing sheets (wait to delete any that were removed)
    # If we delete first, could throw error where we try to delete the last remaining ws
    remote_sheets = {}
    for sheet in spreadsheet.worksheets():
        sheet_title = sheet.title
        requests = {
            "requests": [
                {"updateCells": {"range": {"sheetId": sheet.id}, "fields": "*"}}
            ]
        }
        spreadsheet.batch_update(requests)

        if sheet_title in renamed_local:
            # Maybe rename
            new_title = renamed_local[sheet_title]["new"]
            logging.info(f"Renaming remote sheet '{sheet_title}' to {new_title}")
            sheet.update_title(new_title)
            remote_sheets[new_title] = sheet
        else:
            remote_sheets[sheet_title] = sheet

    # Get formatting and notes on the sheets
    sheet_formats = get_sheet_formats()
    id_to_format = get_format_dict()
    sheet_notes = get_sheet_notes()

    # Add formatting
    for sheet_title, cell_to_format in sheet_formats.items():
        sheet = spreadsheet.worksheet(sheet_title)
        formats = []
        for cell, fmt_id in cell_to_format.items():
            fmt = id_to_format[int(fmt_id)]
            cell_format = gf.CellFormat.from_props(fmt)
            formats.append((cell, cell_format))
        gf.format_cell_ranges(sheet, formats)

    # Add notes
    add_notes(spreadsheet, sheet_notes, tracked_sheets)

    # Get existing fields (headers) to see if we need to add/remove fields
    headers = []

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
            header = next(reader)
            rows.append(header)
            headers.extend(header)
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

        # Add frozen rows & cols
        frozen_row = int(details["Frozen Rows"])
        frozen_col = int(details["Frozen Columns"])
        sheet.freeze(frozen_row, frozen_col)

        # Copy this table into COGS data
        with open(f".cogs/{sheet_title}.tsv", "w") as f:
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerows(rows)

    # Remove sheets if needed
    for sheet_title, sheet in remote_sheets.items():
        if sheet_title not in tracked_sheets.keys():
            logging.info(f"removing sheet '{sheet_title}'")
            # Remove remote copy
            spreadsheet.del_worksheet(sheet)
            # Remove cached copy
            if os.path.exists(f".cogs/{sheet_title}.tsv"):
                os.remove(f".cogs/{sheet_title}.tsv")

    # Maybe update fields if they have changed
    maybe_update_fields(headers)

    with open(".cogs/sheet.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["ID", "Title", "Path", "Description", "Frozen Rows", "Frozen Columns"],
        )
        writer.writeheader()
        writer.writerows(sheet_rows)

    # Remove renamed tracking
    if os.path.exists(".cogs/renamed.tsv"):
        os.remove(".cogs/renamed.tsv")


def run(args):
    """Wrapper for push function."""
    try:
        push(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
