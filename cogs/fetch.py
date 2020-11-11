import csv
import datetime
import json
import logging
import os
import re

import gspread.utils
import gspread_formatting as gf

from cogs.helpers import (
    get_credentials,
    get_config,
    get_format_dict,
    get_renamed_sheets,
    get_tracked_sheets,
    get_cached_sheets,
    set_logging,
    validate_cogs_project,
    get_client_from_config,
    maybe_update_fields,
    update_data_validation,
    update_format,
    update_note,
    update_sheet,
)
from googleapiclient import discovery
from googleapiclient.discovery_cache.base import Cache


class MemoryCache(Cache):
    """Workaround from https://github.com/googleapis/google-api-python-client/issues/325 -
    google-api-python-client is not compatible with oauth2client >= 4.0.0"""

    _CACHE = {}

    def get(self, url):
        return MemoryCache._CACHE.get(url)

    def set(self, url, content):
        MemoryCache._CACHE[url] = content


def clean_data_validation_rules(dv_rules, str_to_rule):
    """Clean up the data validation rules retrieved from the sheets and format them to store in
    validiation.tsv. This also aggregates the rules by ranges."""
    # Aggregate rules by range
    agg_dv_rules = {}
    for dv_rule_str, locs in dv_rules.items():
        dv_rule = str_to_rule[dv_rule_str]
        prev_loc = None
        range_start = None
        locs = sorted(locs)
        agg_locs = []
        for loc in locs:
            row, col = gspread.utils.a1_to_rowcol(loc)
            if not prev_loc:
                prev_loc = loc
                range_start = loc
            else:
                prev_row, prev_col = gspread.utils.a1_to_rowcol(prev_loc)
                if (prev_col == col and prev_row == row - 1) or (
                    prev_row == row and prev_col == col - 1
                ):
                    prev_loc = loc
                else:
                    if prev_loc == range_start:
                        agg_locs.append(prev_loc)
                    else:
                        agg_locs.append(f"{range_start}:{prev_loc}")
                    prev_loc = loc
                    range_start = loc
        # Handle last remaining location
        if prev_loc:
            if prev_loc == range_start:
                agg_locs.append(prev_loc)
            else:
                agg_locs.append(f"{range_start}:{prev_loc}")
        # Create loc -> rule map
        for loc in agg_locs:
            agg_dv_rules[loc] = dv_rule

    # Format the data validation for validation.tsv
    dv_rows = []
    for loc, dv_rule in agg_dv_rules.items():
        condition = dv_rule.condition.type
        values = []
        for cv in dv_rule.condition.values:
            values.append(cv.userEnteredValue)
        dv_rows.append({"Range": loc, "Condition": condition, "Value": ", ".join(values)})

    return dv_rows


def get_cell_data(cogs_dir, sheet):
    """Get cell data from a remote sheet. Cell data includes formatting and notes.
    Return as a map of cell location (e.g., B2) to {"format": dict, "note": str}."""
    # Label is the range of cells in a sheet (e.g., foo!A1:B2)
    spreadsheet_id = sheet.spreadsheet.id
    sheet_name = sheet.title

    # Retrieve the credentials object to send request
    config = get_config(cogs_dir)
    if "Credentials" in config:
        credentials = get_credentials(config["Credentials"])
    else:
        credentials = get_credentials()

    # Build service to send request & execute
    service = discovery.build("sheets", "v4", credentials=credentials, cache=MemoryCache())
    request = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id, ranges=sheet_name, fields="sheets(data(rowData(values(*))))",
    )
    resp = request.execute()

    # Process response
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
            if "dataValidation" in cell:
                condition = cell["dataValidation"]["condition"]
                condition_type = condition["type"]
                values = []
                if "values" in condition:
                    values = [v for v in condition["values"]]
                cell_data["data_validation"] = {"condition": condition_type, "value": values}

            cells[label] = cell_data
            idx_x += 1
        idx_y += 1
    return cells


def get_remote_sheets(sheets):
    """Retrieve a map of sheet title -> sheet ID from the spreadsheet."""
    # Validate sheet titles before downloading anything
    remote_sheets = {}
    for sheet in sheets:
        remote_sheets[sheet.title] = sheet.id
    return remote_sheets


def get_updated_sheet_details(tracked_sheets, remote_sheets, sheet_frozen):
    """Format details from the various dicts to create rows for sheet.tsv."""
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
    return all_sheets


def remove_sheets(cogs_dir, sheets, tracked_sheets, renamed_local, renamed_remote):
    """Remove tracked sheets that are no longer in the remote spreadsheet.
    Return the titles of these sheets."""
    # Get all cached sheet titles
    cached_sheet_titles = get_cached_sheets(cogs_dir)
    new_local_titles = {
        re.sub(r"[^A-Za-z0-9]+", "_", details["new"].lower()): details["new"]
        for details in renamed_local.values()
    }
    new_remote_titles = {
        re.sub(r"[^A-Za-z0-9]+", "_", details["new"].lower()): details["new"]
        for details in renamed_remote.values()
    }
    remote_titles = {re.sub(r"[^A-Za-z0-9]+", "_", x.title.lower()): x.title for x in sheets}
    for sheet_title in cached_sheet_titles:
        if (
            sheet_title not in remote_titles
            and sheet_title not in new_local_titles
            and sheet_title not in new_remote_titles
        ):
            # This sheet has a cached copy but does not exist in the remote version
            # It has either been removed from remote or was newly added to cache
            if (
                sheet_title in tracked_sheets and str(tracked_sheets[sheet_title]["ID"]).strip != ""
            ) or (sheet_title not in tracked_sheets):
                # The sheet is in tracked sheets and has an ID (not newly added)
                # or the sheet is not in tracked sheets
                logging.info(f"Removing untracked '{sheet_title}'")
                if os.path.exists(f"{cogs_dir}/tracked/{sheet_title}.tsv"):
                    os.remove(f"{cogs_dir}/tracked/{sheet_title}.tsv")
    return list(renamed_remote.keys())


def get_sheet_details(sheet_title, sid, sheet_frozen, tracked_sheets):
    """Get the sheet details formatted for sheet.tsv."""
    sheet_paths = {
        details["Path"]: loc_sheet_title for loc_sheet_title, details in tracked_sheets.items()
    }
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
    logging.info(f"new sheet '{sheet_title}' added to project with local path {sheet_path}")
    details = {
        "ID": sid,
        "Title": sheet_title,
        "Path": sheet_path,
        "Description": "",
        "Frozen Rows": frozen_row,
        "Frozen Columns": frozen_col,
    }
    return details


def fetch(verbose=False):
    """Fetch all sheets from project spreadsheet to .cogs/ directory."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()

    config = get_config(cogs_dir)
    gc = get_client_from_config(config)
    spreadsheet = gc.open_by_key(config["Spreadsheet ID"])

    # Get existing fields (headers) to see if we need to add/remove fields
    headers = []

    # Get the remote sheets from spreadsheet
    sheets = spreadsheet.worksheets()
    remote_sheets = get_remote_sheets(sheets)
    tracked_sheets = get_tracked_sheets(cogs_dir, include_no_id=False)
    id_to_title = {
        int(details["ID"]): sheet_title for sheet_title, details in tracked_sheets.items()
    }

    # Get details about renamed sheets
    renamed_local = get_renamed_sheets(cogs_dir)
    renamed_remote = {}

    # Format ID to format for cell formatting
    id_to_format = get_format_dict(cogs_dir)
    if id_to_format:
        # Format to format ID
        format_to_id = {json.dumps(v, sort_keys=True): k for k, v in id_to_format.items()}
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
    sheet_dv_rules = {}
    sheet_frozen = {}
    for sheet in sheets:
        remote_title = sheet.title
        # Download the sheet as the renamed sheet if necessary
        if remote_title in renamed_local:
            st = renamed_local[remote_title]["new"]
            logging.info(f"Downloading remote sheet '{remote_title}' as {st} (renamed locally)")
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
                    renamed_remote[local_title] = {
                        "new": st,
                        "path": re.sub(r"[^A-Za-z0-9]+", "_", st.lower()) + ".tsv",
                    }
            logging.info(f"Downloading remote sheet '{st}'")

        # Get frozen rows & columns
        sheet_frozen[st] = {
            "row": sheet.frozen_row_count,
            "col": sheet.frozen_col_count,
        }

        # Get the cells with format, value, and note from remote sheet
        cells = get_cell_data(cogs_dir, sheet)

        # Create a map of rule -> locs for data validation
        dv_rules = {}
        str_to_rule = {}
        for loc, cell_data in cells.items():
            if "data_validation" not in cell_data:
                continue
            data_validation = cell_data["data_validation"]
            condition = data_validation["condition"]
            bc = gf.BooleanCondition(condition, data_validation["value"])
            dv = gf.DataValidationRule(bc)
            if str(dv) not in str_to_rule:
                str_to_rule[str(dv)] = dv
            if str(dv) in dv_rules:
                locs = dv_rules[str(dv)]
            else:
                locs = []
            locs.append(loc)
            dv_rules[str(dv)] = locs

        # Aggregate by location and format for validate.tsv
        dv_rows = clean_data_validation_rules(dv_rules, str_to_rule)
        sheet_dv_rules[st] = dv_rows

        # Get the ending row & col that have values
        # Otherwise we end up with a bunch of empty rows/columns
        # Also get the data validation
        max_row = 0
        max_col = 0

        for c in cells.keys():
            row, col = gspread.utils.a1_to_rowcol(c)
            if row > max_row:
                max_row = row
            if col > max_col:
                max_col = col

        # Cell label to format dict
        cell_to_format = {cell: data["format"] for cell, data in cells.items() if "format" in data}

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
                        cell_to_format_id[f"{cell_range_start}:{cell_range_end}"] = last_fmt
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
        cell_to_note = {cell: data["note"] for cell, data in cells.items() if "note" in data}
        if cell_to_note:
            sheet_notes[st] = cell_to_note

        # Write values to .cogs/tracked/{sheet title}.tsv
        sheet_path = re.sub(r"[^A-Za-z0-9]+", "_", st.lower()).strip("_")
        with open(f"{cogs_dir}/tracked/{sheet_path}.tsv", "w") as f:
            lines = sheet.get_all_values()
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerows(lines)
            if lines:
                headers.extend(lines[0])

    # Maybe update fields if they have changed
    maybe_update_fields(cogs_dir, headers)

    # Write or rewrite formats JSON with new dict
    with open(f"{cogs_dir}/formats.json", "w") as f:
        f.write(json.dumps(id_to_format, sort_keys=True, indent=4))

    # Update local sheets details in sheet.tsv with new IDs & details for current tracked sheets
    all_sheets = get_updated_sheet_details(tracked_sheets, remote_sheets, sheet_frozen)

    # If a cached sheet title is not in sheet.tsv & not in remote sheets - remove it
    removed_titles = remove_sheets(cogs_dir, sheets, tracked_sheets, renamed_local, renamed_remote)

    # Add renamed-remote
    for old_title, details in renamed_remote.items():
        with open(f"{cogs_dir}/renamed.tsv", "a") as f:
            new_title = details["new"]
            new_path = details["path"]
            f.write(f"{old_title}\t{new_title}\t{new_path}\tremote\n")

    # Rewrite format.tsv and note.tsv with current remote formats & notes
    update_format(cogs_dir, sheet_formats, removed_titles)
    update_note(cogs_dir, sheet_notes, removed_titles)
    # Remove old data validation rules and rewrite with new
    with open(f"{cogs_dir}/validation.tsv", "w") as f:
        f.write("Sheet\tRange\tCondition\tValue\n")
    update_data_validation(cogs_dir, sheet_dv_rules, removed_titles)

    # Get just the remote sheets that are not in local sheets
    new_sheets = {
        sheet_title: sid
        for sheet_title, sid in remote_sheets.items()
        if sheet_title not in tracked_sheets
    }
    for sheet_title, sid in new_sheets.items():
        if sheet_title not in renamed_local:
            details = get_sheet_details(sheet_title, sid, sheet_frozen, tracked_sheets)
            all_sheets.append(details)

    # Then update sheet.tsv
    update_sheet(cogs_dir, all_sheets, removed_titles)
