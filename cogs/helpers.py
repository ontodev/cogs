import csv
import google.auth.exceptions
import gspread
import json
import logging
import os
import pkg_resources
import re

from cogs.exceptions import CogsError
from daff import Coopy, CompareFlags, PythonTableView, TableDiff
from google.oauth2.service_account import Credentials


required_files = [
    "config.tsv",
    "field.tsv",
    "format.tsv",
    "note.tsv",
    "sheet.tsv",
    "validation.tsv",
]
optional_files = ["user.tsv", "renamed.tsv"]

required_keys = ["Spreadsheet ID", "Title"]

credential_keys = []


def get_cached_sheets(cogs_dir):
    """Return a list of names of cached sheets from .cogs/tracked. These are any sheets that have
    been downloaded from the remote spreadsheet into the .cogs directory as TSVs. They may or may
    not be tracked in sheet.tsv."""
    return [f.split(".")[0] for f in os.listdir(f"{cogs_dir}/tracked")]


def get_json_credentials(credentials_path=None):
    """Get the Google credentials as a dictionary."""
    if not credentials_path:
        # No path provided, use environment variable
        env = os.environ
        if "GOOGLE_CREDENTIALS" not in env:
            raise CogsError(
                "Unable to create a Client; GOOGLE_CREDENTIALS environment variable is not set"
            )
        credentials = json.loads(env["GOOGLE_CREDENTIALS"])
    else:
        # Otherwise load from credentials path
        try:
            credentials = json.load(open(credentials_path))
        except FileNotFoundError:
            raise CogsError(
                f"Unable to create a Client; credentials file at {credentials_path} does not exist"
            )
    return credentials


def get_credentials(credentials_path=None):
    """Get the credentials as a Credentials object with scopes."""
    credentials = get_json_credentials(credentials_path=credentials_path)

    try:
        # Create Credentials object and add scope (spreadsheets & drive)
        gcred = Credentials.from_service_account_info(credentials)
        gcred = gcred.with_scopes(
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
        )
    except ValueError as ve:
        # credentials are missing a required key
        raise CogsError(f"Unable to create a Client from credentials; {str(ve)}")
    return gcred


def get_client(credentials_path=None):
    """Get the google.auth Client to perform Google Sheets API actions."""
    # First get the credentials JSON
    gcred = get_credentials(credentials_path=credentials_path)
    try:
        # Create gspread Client & log in
        gc = gspread.Client(auth=gcred)
        gc.login()
        return gc

    except gspread.exceptions.APIError as e:
        raise CogsError(f"Unable to create a Client from credentials; {e.response.text}")
    except google.auth.exceptions.RefreshError as e:
        if "invalid_grant" in str(e):
            raise CogsError("Unable to create a Client; account for client_email cannot be found")
        else:
            raise CogsError(f"Unable to create a Client; {str(e)}")


def get_client_from_config(config):
    """Get the google.auth client from COGS configuration."""
    if "Credentials" in config:
        return get_client(config["Credentials"])
    else:
        return get_client()


def get_config(cogs_dir):
    """Get the configuration for this project as a dict."""
    config = {}
    with open(f"{cogs_dir}/config.tsv", "r") as f:
        reader = csv.reader(f, delimiter="\t", lineterminator="\n")
        for row in reader:
            config[row[0]] = row[1]
    for r in required_keys:
        if r not in config:
            raise CogsError(f"COGS configuration does not contain key '{r}'")
    return config


def get_data_validation(cogs_dir):
    """Get a dict of sheet title -> data validation rules."""
    sheet_to_dv_rules = {}
    with open(f"{cogs_dir}/validation.tsv") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            sheet_title = row["Sheet Title"]
            del row["Sheet Title"]
            if sheet_title in sheet_to_dv_rules:
                dv_rules = sheet_to_dv_rules[sheet_title]
            else:
                dv_rules = []
            dv_rules.append(row)
            sheet_to_dv_rules[sheet_title] = dv_rules
    return sheet_to_dv_rules


def get_diff(local, remote):
    """Return the diff between a local and remote sheet as a list of lines (list of cell values)
    with daff 'highlighter' formatting. The 'highlight' is appended to the beginning of the line as:
    - '+++' for added lines
    - '->' for changed lines
    - '...' for omitted rows
    - '---' for removed lines
    - '' for unchanged lines
    The remote table is the 'old' version and the local table is the 'new' version."""
    local_data = []
    with open(local, "r") as f:
        # Local might be CSV or TSV
        if local.endswith("csv"):
            reader = csv.reader(f)
        else:
            reader = csv.reader(f, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            # No data
            header = None
        if header:
            local_data.append(header)
            for row in reader:
                if len(row) < len(header):
                    add = [""] * (len(header) - len(row))
                    row.extend(add)
                local_data.append(row)

    remote_data = []
    with open(remote, "r") as f:
        # Remote is always TSV
        reader = csv.reader(f, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            # No data
            header = None
        if header:
            remote_data.append(header)
            for row in reader:
                if len(row) < len(header):
                    add = [""] * (len(header) - len(row))
                    row.extend(add)
                remote_data.append(row)

    if not local_data and not remote_data:
        return []

    local_table = PythonTableView(local_data)
    remote_table = PythonTableView(remote_data)
    align = Coopy.compareTables(remote_table, local_table).align()

    data_diff = []
    table_diff = PythonTableView(data_diff)
    flags = CompareFlags()
    highlighter = TableDiff(align, flags)
    highlighter.hilite(table_diff)

    return data_diff


def get_fields(cogs_dir):
    """Get the current fields in this project from field.tsv as a dict of field name -> details."""
    fields = {}
    with open(f"{cogs_dir}/field.tsv", "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            field = row["Field"]
            del row["Field"]
            fields[field] = row
    return fields


def get_format_dict(cogs_dir):
    """Get a dict of numerical format ID -> the format dict."""
    if (
        os.path.exists(f"{cogs_dir}/formats.json")
        and not os.stat(f"{cogs_dir}/formats.json").st_size == 0
    ):
        with open(f"{cogs_dir}/formats.json", "r") as f:
            fmt_dict = json.loads(f.read())
            return {int(k): v for k, v in fmt_dict.items()}
    return {}


def get_sheet_formats(cogs_dir):
    """Get a dict of sheet ID -> formatted cells."""
    sheet_to_formats = {}
    with open(f"{cogs_dir}/format.tsv") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            sheet_title = row["Sheet Title"]
            cell = row["Cell"]
            fmt = int(row["Format ID"])
            if sheet_title in sheet_to_formats:
                cell_to_format = sheet_to_formats[sheet_title]
            else:
                cell_to_format = {}
            cell_to_format[cell] = fmt
            sheet_to_formats[sheet_title] = cell_to_format
    return sheet_to_formats


def get_sheet_notes(cogs_dir):
    """Get a dict of sheet ID -> notes on cells."""
    sheet_to_notes = {}
    with open(f"{cogs_dir}/note.tsv") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            sheet_title = row["Sheet Title"]
            cell = row["Cell"]
            note = row["Note"]
            if sheet_title in sheet_to_notes:
                cell_to_note = sheet_to_notes[sheet_title]
            else:
                cell_to_note = {}
            cell_to_note[cell] = note
            sheet_to_notes[sheet_title] = cell_to_note
    return sheet_to_notes


def get_sheet_url(config=None):
    """Return the URL of the spreadsheet."""
    if not config:
        cogs_dir = validate_cogs_project()
        config = get_config(cogs_dir)
    spreadsheet_id = config["Spreadsheet ID"]
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"


def get_renamed_sheets(cogs_dir):
    """Get a set of renamed sheets from renamed.tsv as a dict of old name -> new name & path."""
    renamed = {}
    if os.path.exists(f"{cogs_dir}/renamed.tsv"):
        with open(f"{cogs_dir}/renamed.tsv", "r") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                renamed[row[0]] = {"new": row[1], "path": row[2], "where": row[3]}
    return renamed


def get_tracked_sheets(cogs_dir, include_no_id=True):
    """Get the current tracked sheets in this project from sheet.tsv as a dict of sheet title ->
    path & ID. They may or may not have corresponding cached/local sheets."""
    sheets = {}
    with open(f"{cogs_dir}/sheet.tsv", "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            title = row["Title"]
            if not title:
                continue
            sheet_id = row["ID"]
            if not include_no_id and sheet_id == "":
                continue
            del row["Title"]
            sheets[title] = row
    return sheets


def get_version():
    """Get the version of COGS."""
    try:
        version = pkg_resources.require("COGS")[0].version
    except pkg_resources.DistributionNotFound:
        version = "developer-version"
    return version


def is_email(email):
    """Check if a string matches a general email pattern (user@domain.tld)"""
    return re.match(r"^[-.\w]+@[-\w]+\.[-\w]+$", email)


def is_valid_role(role):
    """Check if a string is a valid role for use with gspread."""
    return role in ["writer", "reader"]


def maybe_update_fields(cogs_dir, headers):
    """Given a list of headers, check if any fields were added or removed and update the field.tsv
    if necessary."""
    fields = get_fields(cogs_dir)
    update_fields = False
    # Determine if fields were removed
    new_fields = {re.sub(r"[^A-Za-z0-9]+", "_", h.lower()).strip("_"): h for h in headers}
    remove_fields = [f for f in fields.keys() if f not in new_fields.keys()]
    if remove_fields:
        update_fields = True
        for rf in remove_fields:
            del fields[rf]

    # Determine if fields were added
    for f, h in new_fields.items():
        if f not in fields:
            update_fields = True
            fields[f] = {
                "Label": h,
                "Datatype": "cogs:text",
                "Description": "",
            }

    # Update the field file if fields were added or removed
    if update_fields:
        with open(f"{cogs_dir}/field.tsv", "w") as f:
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


def set_logging(verbose):
    """Set logging for COGS based on -v/--verbose."""
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


def update_format(cogs_dir, sheet_formats, removed_titles):
    """Update format.tsv with current remote formatting.
    Remove any lines with a Sheet ID in removed_ids."""
    current_sheet_formats = get_sheet_formats(cogs_dir)
    fmt_rows = []
    for sheet_title, formats in sheet_formats.items():
        current_sheet_formats[sheet_title] = formats
    for sheet_title, formats in current_sheet_formats.items():
        if sheet_title in removed_titles:
            continue
        for cell, fmt in formats.items():
            fmt_rows.append({"Sheet Title": sheet_title, "Cell": cell, "Format ID": fmt})
    with open(f"{cogs_dir}/format.tsv", "w") as f:
        writer = csv.DictWriter(
            f, delimiter="\t", lineterminator="\n", fieldnames=["Sheet Title", "Cell", "Format ID"],
        )
        writer.writeheader()
        writer.writerows(fmt_rows)


def update_note(cogs_dir, sheet_notes, removed_titles):
    """Update note.tsv with current remote notes.
    Remove any lines with a Sheet ID in removed_ids."""
    current_sheet_notes = get_sheet_notes(cogs_dir)
    note_rows = []
    for sheet_title, notes in sheet_notes.items():
        current_sheet_notes[sheet_title] = notes
    for sheet_title, notes in current_sheet_notes.items():
        if sheet_title in removed_titles:
            continue
        for cell, note in notes.items():
            note_rows.append({"Sheet Title": sheet_title, "Cell": cell, "Note": note})
    with open(f"{cogs_dir}/note.tsv", "w") as f:
        writer = csv.DictWriter(
            f, delimiter="\t", lineterminator="\n", fieldnames=["Sheet Title", "Cell", "Note"],
        )
        writer.writeheader()
        writer.writerows(note_rows)


def update_data_validation(cogs_dir, sheet_dv_rules, removed_titles):
    """"""
    # TODO - can we be smarter and error on overlap?
    current_sheet_dv_rules = get_data_validation(cogs_dir)
    dv_rows = []
    for sheet_title, dv_rules in sheet_dv_rules.items():
        if sheet_title in current_sheet_dv_rules:
            current_dv_rules = current_sheet_dv_rules[sheet_title]
        else:
            current_dv_rules = []
        current_dv_rules.extend(dv_rules)
        current_sheet_dv_rules[sheet_title] = current_dv_rules
    for sheet_title, dv_rules in current_sheet_dv_rules.items():
        if sheet_title in removed_titles:
            continue
        for row in dv_rules:
            row["Sheet Title"] = sheet_title
            dv_rows.append(row)
    with open(f"{cogs_dir}/validation.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["Sheet Title", "Range", "Condition", "Value"],
        )
        writer.writeheader()
        writer.writerows(dv_rows)


def update_sheet(cogs_dir, sheet_details, removed_titles):
    """"""
    rows = [details for details in sheet_details if details["Title"] not in removed_titles]
    with open(f"{cogs_dir}/sheet.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["ID", "Title", "Path", "Description", "Frozen Rows", "Frozen Columns"],
        )
        writer.writeheader()
        writer.writerows(rows)


def validate_cogs_project():
    """Validate that there is a valid COGS project in this or the parents of this directory. If not,
    raise an error. Return the absolute path of the .cogs directory."""
    cur_dir = os.getcwd()
    cogs_dir = None
    while cur_dir != "/":
        if ".cogs" in os.listdir(cur_dir):
            cogs_dir = os.path.join(cur_dir, ".cogs")
        cur_dir = os.path.abspath(os.path.join(cur_dir, ".."))

    if not cogs_dir:
        raise CogsError("A COGS project has not been initialized in this or parent directories!")
    for r in required_files:
        if not os.path.exists(f"{cogs_dir}/{r}") or os.stat(f"{cogs_dir}/{r}").st_size == 0:
            raise CogsError(f"COGS directory '{cogs_dir}' is missing {r}")

    return cogs_dir
