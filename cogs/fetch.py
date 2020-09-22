import datetime
import gspread.utils
import sys

from cogs.exceptions import FetchError
from cogs.helpers import *


def msg():
    return "Fetch remote versions of sheets"


def get_cell_data(sheet):
    """Get cell data from a remote sheet. Cell data includes formatting and notes.
    Return as a map of cell location (e.g., B2) to {"format": dict, "note": str}."""
    # Label is the range of cells in a sheet (e.g., foo!A1:B2)
    last_loc = gspread.utils.rowcol_to_a1(sheet.row_count, sheet.col_count)
    label = f"{sheet.title}!A1:{last_loc}"
    resp = sheet.spreadsheet.fetch_sheet_metadata(
        {"includeGridData": True, "ranges": label}
    )
    cells = {}
    idx_y = 1
    data = resp["sheets"][0]["data"][0]
    if "rowData" not in data:
        # Empty sheet
        return cells
    for row in data["rowData"]:
        if not row:
            # Empty row
            continue
        idx_x = 1
        for cell in row["values"]:
            label = gspread.utils.rowcol_to_a1(idx_y, idx_x)
            cell_data = {}
            if "userEnteredFormat" in cell:
                cell_data["format"] = cell["userEnteredFormat"]
            else:
                cell_data["format"] = {}
            if "note" in cell:
                cell_data["note"] = cell["note"].replace("\n", "\\n")
            cells[label] = cell_data
            idx_x += 1
        idx_y += 1
    return cells


def get_remote_sheets(sheets):
    """Retrieve a map of sheet title -> sheet ID from the spreadsheet."""
    # Validate sheet titles before downloading anything
    remote_sheets = {}
    for sheet in sheets:
        if sheet.title in ["user", "config", "sheet", "field", "renamed"]:
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
    gc = get_client_from_config(config)
    title = config["Title"]
    spreadsheet = gc.open(title)

    # Get existing fields (headers) to see if we need to add/remove fields
    headers = []

    # Get the remote sheets from spreadsheet
    sheets = spreadsheet.worksheets()
    remote_sheets = get_remote_sheets(sheets)
    tracked_sheets = get_tracked_sheets(include_no_id=False)
    id_to_title = {
        int(details["ID"]): sheet_title
        for sheet_title, details in tracked_sheets.items()
    }

    # Get details about renamed sheets
    renamed_local = get_renamed_sheets()
    new_local_titles = [details["new"] for details in renamed_local.values()]
    renamed_remote = {}

    # Format ID to format for cell formatting
    id_to_format = get_format_dict()
    if id_to_format:
        # Format to format ID
        format_to_id = {
            json.dumps(v, sort_keys=True): k for k, v in id_to_format.items()
        }
        # Next ID for new formats
        format_ids = list(id_to_format.keys())
        format_ids.sort()
        next_fmt_id = int(format_ids[-1]) + 1
    else:
        format_to_id = {}
        next_fmt_id = 1

    # Export the sheets as TSV to .cogs/ (while checking the fieldnames)
    # We also collect the formatting and note data for each sheet during this step
    sheet_formats = {}
    sheet_notes = {}
    sheet_frozen = {}
    for sheet in sheets:
        remote_title = sheet.title
        # Download the sheet as the renamed sheet if necessary
        if remote_title in renamed_local:
            st = renamed_local[remote_title]["new"]
            logging.info(
                f"Downloading remote sheet '{remote_title}' as {st} (renamed locally)"
            )
        else:
            st = remote_title
            if sheet.id in id_to_title:
                local_title = id_to_title[sheet.id]
                if local_title != remote_title:
                    # The sheet title has been changed remotely
                    # This will be updated in tracking but the local sheet will remain
                    old_path = tracked_sheets[local_title]["Path"]
                    logging.warning(
                        f"Local sheet '{local_title}' has been renamed to '{st}' remotely:"
                        f"\n  - '{local_title}' is removed from tracking and replaced with '{st}'"
                        f"\n  - {old_path} will not be updated when running `cogs pull` "
                        f"\n  - changes to {old_path} will not be pushed to the remote spreadsheet"
                    )
                    renamed_remote[local_title] = {"new": st, "path": st + ".tsv"}
            logging.info(f"Downloading remote sheet '{st}'")

        if st in reserved_names:
            # Remote sheet has reserved sheet name - exit
            raise FetchError(f"sheet cannot use reserved name '{st}'")

        # Get frozen rows & columns
        sheet_frozen[st] = {
            "row": sheet.frozen_row_count,
            "col": sheet.frozen_col_count,
        }

        # Get the cells with format, value, and note from remote sheet
        cells = get_cell_data(sheet)

        # Get the ending row & col that have values
        # Otherwise we end up with a bunch of empty rows/columns
        max_row = 0
        max_col = 0
        for c in cells.keys():
            row, col = gspread.utils.a1_to_rowcol(c)
            if row > max_row:
                max_row = row
            if col > max_col:
                max_col = col

        # Cell label to format dict
        cell_to_format = {
            cell: data["format"] for cell, data in cells.items() if "format" in data
        }

        # Create a cell to format ID dict based on the format dict for each cell
        cell_to_format_id = {}
        last_fmt = None
        cell_range_start = None
        cell_range_end = None
        for cell, fmt in cell_to_format.items():
            if not fmt:
                if last_fmt:
                    if not cell_range_end or cell_range_start == cell_range_end:
                        cell_to_format_id[cell_range_start] = last_fmt
                    else:
                        cell_to_format_id[
                            f"{cell_range_start}:{cell_range_end}"
                        ] = last_fmt
                last_fmt = None
                cell_range_start = None
                cell_range_end = None
                continue

            key = json.dumps(fmt, sort_keys=True)

            if key in format_to_id:
                # Format already exists, assign that ID
                fmt_id = format_to_id[key]
            else:
                # Assign new ID
                fmt_id = next_fmt_id
                format_to_id[key] = fmt_id
                id_to_format[fmt_id] = fmt
                next_fmt_id += 1

            if last_fmt and fmt_id == last_fmt:
                # The last cell had a format and the this cell's format is the same as the last
                # so we increase the range
                cell_range_end = cell
            elif last_fmt and fmt_id != last_fmt:
                # The last cell had a format but it was different than the current format
                if cell_range_start == cell_range_end or not cell_range_end:
                    # Not a range, just a single cell (the previous cell)
                    cell_to_format_id[cell_range_start] = last_fmt
                else:
                    cell_to_format_id[f"{cell_range_start}:{cell_range_end}"] = last_fmt
                # Restarting a new range at this cell
                cell_range_start = cell
                cell_range_end = None
            else:
                # No last formatting to compare to, start a new range
                cell_range_start = cell
                cell_range_end = cell
            last_fmt = fmt_id

        if cell_to_format_id:
            sheet_formats[st] = cell_to_format_id

        # Add the cell to note
        cell_to_note = {
            cell: data["note"] for cell, data in cells.items() if "note" in data
        }
        if cell_to_note:
            sheet_notes[st] = cell_to_note

        # Write values to .cogs/{sheet title}.tsv
        with open(f".cogs/{st}.tsv", "w") as f:
            lines = sheet.get_all_values()
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerows(lines)
            if lines:
                headers.extend(lines[0])

    # Maybe update fields if they have changed
    maybe_update_fields(headers)

    # Write or rewrite formats JSON with new dict
    with open(".cogs/formats.json", "w") as f:
        f.write(json.dumps(id_to_format, sort_keys=True, indent=4))

    # Update local sheets with new IDs
    all_sheets = []
    for sheet_title, details in tracked_sheets.items():
        if sheet_title in remote_sheets:
            sid = remote_sheets[sheet_title]
            details["ID"] = sid
            if sheet_title in sheet_frozen:
                frozen = sheet_frozen[sheet_title]
                details["Frozen Rows"] = frozen["row"]
                details["Frozen Columns"] = frozen["col"]
            else:
                details["Frozen Rows"] = 0
                details["Frozen Columns"] = 0
        details["Title"] = sheet_title
        all_sheets.append(details)

    # Get all cached sheet titles that are not COGS defaults
    cached_sheet_titles = get_cached_sheets()

    # If a cached sheet title is not in sheet.tsv & not in remote sheets - remove it
    remote_titles = [x.title for x in sheets]
    removed_titles = []
    for sheet_title in cached_sheet_titles:
        if sheet_title not in remote_titles and sheet_title not in new_local_titles:
            # This sheet has a cached copy but does not exist in the remote version
            # It has either been removed from remote or was newly added to cache
            if (
                sheet_title in tracked_sheets
                and tracked_sheets[sheet_title]["ID"].strip != ""
            ) or (sheet_title not in tracked_sheets):
                # The sheet is in tracked sheets and has an ID (not newly added)
                # or the sheet is not in tracked sheets
                removed_titles.append(sheet_title)
                logging.info(f"Removing '{sheet_title}'")
                os.remove(f".cogs/{sheet_title}.tsv")

    # Rewrite format.tsv and note.tsv with current remote formats & notes
    update_format(sheet_formats, removed_titles)
    update_note(sheet_notes, removed_titles)

    # Get just the remote sheets that are not in local sheets
    sheet_paths = {
        details["Path"]: loc_sheet_title
        for loc_sheet_title, details in tracked_sheets.items()
    }
    new_sheets = {
        sheet_title: sid
        for sheet_title, sid in remote_sheets.items()
        if sheet_title not in tracked_sheets
    }
    for sheet_title, sid in new_sheets.items():
        if sheet_title not in renamed_local:
            if sheet_title in sheet_frozen:
                frozen = sheet_frozen[sheet_title]
                frozen_row = frozen["row"]
                frozen_col = frozen["col"]
            else:
                frozen_row = 0
                frozen_col = 0
            sheet_path = re.sub(r"[^A-Za-z0-9]+", "_", sheet_title.lower()).strip("_")
            # Make sure the path is unique - the user can change this later
            if sheet_path + ".tsv" in sheet_paths.keys():
                # Append datetime if this path already exists
                td = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                sheet_path += f"_{td}.tsv"
            else:
                sheet_path += ".tsv"
            logging.info(
                f"new sheet '{sheet_title}' added to project with local path {sheet_path}"
            )
            details = {
                "ID": sid,
                "Title": sheet_title,
                "Path": sheet_path,
                "Description": "",
                "Frozen Rows": frozen_row,
                "Frozen Columns": frozen_col,
            }
            all_sheets.append(details)

    # Then update sheet.tsv
    with open(".cogs/sheet.tsv", "w") as f:
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
            ],
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
