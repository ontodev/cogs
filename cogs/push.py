import csv
import gspread.exceptions
import gspread.utils
import gspread_formatting as gf
import logging
import os
import re

from cogs.helpers import (
    get_tracked_sheets,
    set_logging,
    validate_cogs_project,
    get_cached_path,
    get_config,
    get_client_from_config,
    get_renamed_sheets,
    get_sheet_formats,
    get_format_dict,
    get_sheet_notes,
    get_data_validation,
)


def clear_remote_sheets(spreadsheet, tracked_sheets, renamed_local):
    """Clear all data from remote sheets and return a map of sheet title -> sheet obj."""
    remote_sheets = {}
    for sheet in spreadsheet.worksheets():
        sheet_title = sheet.title
        if sheet_title in tracked_sheets and tracked_sheets[sheet_title].get("Ignore"):
            remote_sheets[sheet_title] = sheet
            continue

        requests = {"requests": [{"updateCells": {"range": {"sheetId": sheet.id}, "fields": "*"}}]}
        spreadsheet.batch_update(requests)

        if sheet_title in renamed_local:
            # Maybe rename
            new_title = renamed_local[sheet_title]["new"]
            logging.info(f"Renaming remote sheet '{sheet_title}' to {new_title}")
            sheet.update_title(new_title)
            remote_sheets[new_title] = sheet
        else:
            remote_sheets[sheet_title] = sheet
    return remote_sheets


def push_data(cogs_dir, spreadsheet, tracked_sheets, remote_sheets):
    """Push all tracked sheets to the spreadsheet. Update sheets in COGS tracked directory. Return
    updated rows for sheet.tsv."""
    sheet_rows = []
    for sheet_title, details in tracked_sheets.items():
        if details.get("Ignore"):
            logging.info(f"Skipping ignored sheet '{sheet_title}'")
            details["Title"] = sheet_title
            sheet_rows.append(details)
            continue
        sheet_path = details["Path"]
        delimiter = "\t"
        if sheet_path.endswith(".csv"):
            delimiter = ","
        rows = []
        cols = 0
        if not os.path.exists(sheet_path):
            logging.warning(f"'{sheet_title}' exists remotely but has not been pulled")
            continue
        with open(sheet_path, "r") as fr:
            reader = csv.reader(fr, delimiter=delimiter)
            tracked_sheet = get_cached_path(cogs_dir, sheet_title)
            with open(tracked_sheet, "w") as fw:
                writer = csv.writer(fw, delimiter="\t", lineterminator="\n")
                for row in reader:
                    writer.writerow(row)
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

        logging.info(f"pushing data from {sheet_path} to remote sheet '{sheet_title}'")

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
        cached_name = get_cached_path(cogs_dir, sheet_title)
        with open(cached_name, "w") as f:
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerows(rows)
    return sheet_rows


def push_data_validation(spreadsheet, data_validation, tracked_sheets):
    """Add data validation rules from validation.tsv to the spreadsheet."""
    requests = []
    for sheet_title, dv_rules in data_validation.items():
        sheet_id = tracked_sheets[sheet_title]["ID"]
        for dv_rule in dv_rules:
            dv_range = dv_rule["Range"]
            if ":" in dv_range:
                start = dv_range.split(":")[0]
                end = dv_range.split(":")[1]
            else:
                start = dv_range
                end = dv_range
            start_row, start_col = gspread.utils.a1_to_rowcol(start)
            end_row, end_col = gspread.utils.a1_to_rowcol(end)
            condition = dv_rule["Condition"]
            value_str = dv_rule["Value"]
            values = []
            if value_str != "":
                values = re.compile(r"(?<!\\), ").split(value_str)
            values = [re.sub(r"\\([^\\])", r"\1", x) for x in values]
            value_obj = []
            for v in values:
                value_obj.append({"userEnteredValue": v})
            show_ui = False
            if condition.endswith("LIST"):
                show_ui = True
            requests.append(
                {
                    "updateCells": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row - 1,
                            "endRowIndex": end_row,
                            "startColumnIndex": start_col - 1,
                            "endColumnIndex": end_col,
                        },
                        "rows": [
                            {
                                "values": {
                                    "dataValidation": {
                                        "condition": {"type": condition, "values": value_obj},
                                        "showCustomUi": show_ui,
                                    }
                                }
                            }
                        ],
                        "fields": "dataValidation",
                    }
                }
            )
    if not requests:
        return
    try:
        logging.info(f"adding {len(requests)} data validation rules to spreadsheet")
        spreadsheet.batch_update({"requests": requests})
    except gspread.exceptions.APIError as e:
        logging.error(
            f"Unable to add {len(requests)} data validation rules to spreadsheet\n"
            + e.response.text
        )


def push_formats(spreadsheet, id_to_format, sheet_formats):
    """Batch add formats to a spreadsheet."""
    for sheet_title, cell_to_format in sheet_formats.items():
        worksheet = spreadsheet.worksheet(sheet_title)
        requests = []
        for cell, fmt_id in cell_to_format.items():
            fmt = id_to_format[int(fmt_id)]
            cell_format = gf.CellFormat.from_props(fmt)
            requests.append((cell, cell_format))
        if requests:
            logging.info(f"adding {len(requests)} formats to sheet '{sheet_title}")
            gf.format_cell_ranges(worksheet, requests)


def push_notes(spreadsheet, sheet_notes, tracked_sheets):
    """Batch add notes to a spreadsheet."""
    requests = []
    for sheet_title, cell_to_note in sheet_notes.items():
        sheet_id = tracked_sheets[sheet_title]["ID"]
        for cell, note in cell_to_note.items():
            row, col = gspread.utils.a1_to_rowcol(cell)
            requests.append(
                {
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
                }
            )
    if not requests:
        return
    try:
        logging.info(f"adding {len(requests)} notes to spreadsheet")
        spreadsheet.batch_update({"requests": requests})
    except gspread.exceptions.APIError as e:
        logging.error(f"Unable to add {len(requests)} notes to spreadsheet\n" + e.response.text)


def push(verbose=False):
    """Push local tables to the spreadsheet as sheets. Only the sheets in sheet.tsv will be
    pushed. If a sheet in the Sheet does not exist in the local sheet.tsv, it will be removed
    from the Sheet. Any sheet in sheet.tsv that does not exist in the Sheet will be created.
    Any sheet in sheet.tsv that does exist will be updated."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()
    config = get_config(cogs_dir)
    gc = get_client_from_config(config)
    spreadsheet = gc.open_by_key(config["Spreadsheet ID"])

    # Get tracked sheets
    tracked_sheets = get_tracked_sheets(cogs_dir)
    renamed_local = get_renamed_sheets(cogs_dir)

    # Clear existing sheets (wait to delete any that were removed)
    # If we delete first, could throw error where we try to delete the last remaining ws
    remote_sheets = clear_remote_sheets(spreadsheet, tracked_sheets, renamed_local)

    # Add new data to the sheets in the Sheet and return headers & sheets details
    sheet_rows = push_data(cogs_dir, spreadsheet, tracked_sheets, remote_sheets)

    # Remove sheets from remote if needed
    for sheet_title, sheet in remote_sheets.items():
        if sheet_title not in tracked_sheets.keys():
            logging.info(f"removing sheet '{sheet_title}'")
            # Remove remote copy
            spreadsheet.del_worksheet(sheet)
            # Remove cached copy
            if os.path.exists(f"{cogs_dir}/tracked/{sheet_title}.tsv"):
                os.remove(f"{cogs_dir}/tracked/{sheet_title}.tsv")

    # Get formatting and notes on the sheets
    sheet_formats = get_sheet_formats(cogs_dir)
    id_to_format = get_format_dict(cogs_dir)
    sheet_notes = get_sheet_notes(cogs_dir)
    data_validation = get_data_validation(cogs_dir)

    # Add formatting, notes, and data validation
    push_data_validation(spreadsheet, data_validation, tracked_sheets)
    push_formats(spreadsheet, id_to_format, sheet_formats)
    push_notes(spreadsheet, sheet_notes, tracked_sheets)

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
        writer.writerows(sheet_rows)

    # Remove renamed tracking
    if os.path.exists(f"{cogs_dir}/renamed.tsv"):
        os.remove(f"{cogs_dir}/renamed.tsv")
