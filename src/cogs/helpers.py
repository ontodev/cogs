import csv
import google.auth.exceptions
import gspread
import logging
import os
import pkg_resources
import re

from cogs.exceptions import CogsError
from daff import Coopy, CompareFlags, PythonTableView, TableDiff

required_files = ["sheet.tsv", "field.tsv", "config.tsv"]

required_keys = ["Spreadsheet ID", "Title", "Credentials"]


def get_cached():
    """Return a list of cached sheets from .cogs."""
    cached = []
    for f in os.listdir(".cogs"):
        if f not in ["user.tsv", "sheet.tsv", "field.tsv", "config.tsv", "renamed.tsv"]:
            cached.append(f.split(".")[0])
    return cached


def get_diff(local, remote):
    """Return the diff between a local and remote sheet as a list of lines with formatting. The
       remote table is the 'old' version and the local table is the 'new' version."""
    local_data = []
    with open(local, "r") as f:
        # Local might be CSV or TSV
        if local.endswith("csv"):
            reader = csv.reader(f)
        else:
            reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        local_data.append(header)
        for row in reader:
            if len(row) < len(header):
                add = [''] * (len(header) - len(row))
                row.extend(add)
            local_data.append(row)

    remote_data = []
    with open(remote, "r") as f:
        # Remote is always TSV
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        remote_data.append(header)
        for row in reader:
            if len(row) < len(header):
                add = [''] * (len(header) - len(row))
                row.extend(add)
            remote_data.append(row)

    local_table = PythonTableView(local_data)
    remote_table = PythonTableView(remote_data)
    align = Coopy.compareTables(remote_table, local_table).align()

    data_diff = []
    table_diff = PythonTableView(data_diff)
    flags = CompareFlags()
    highlighter = TableDiff(align, flags)
    highlighter.hilite(table_diff)

    return data_diff


def get_client(credentials):
    """Get the gspread Client to perform Google Sheets API actions."""
    try:
        gc = gspread.service_account(credentials)
        gc.login()
        return gc
    except gspread.exceptions.APIError as e:
        print(f"Unable to create a Client from credentials '{credentials}'")
        print(e.response.text)
    except google.auth.exceptions.RefreshError as e:
        if "invalid_grant" in str(e):
            raise CogsError(
                "Unable to create a Client; "
                f"account for client_email in '{credentials}' cannot be found"
            )
        else:
            raise CogsError(
                f"Unable to create a Client; cannot refresh credentials in '{credentials}'"
                f"\nCAUSE: {str(e)}"
            )


def get_colstr(n):
    """Transform an int (corresponding to a column) to a letter column for use in Google Sheets"""
    string = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string


def get_config():
    """Get the configuration for this project as a dict."""
    config = {}
    with open(".cogs/config.tsv", "r") as f:
        reader = csv.reader(f, delimiter="\t", lineterminator="\n")
        for row in reader:
            config[row[0]] = row[1]
    for r in required_keys:
        if r not in config:
            raise CogsError(f"COGS configuration does not contain key '{r}'")
    return config


def get_fields():
    """Get the current fields in this project from field.tsv."""
    fields = {}
    with open(".cogs/field.tsv", "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            field = row["Field"]
            del row["Field"]
            fields[field] = row
    return fields


def get_renamed():
    """Get a set of renamed sheets from renamed.tsv."""
    renamed = {}
    if os.path.exists(".cogs/renamed.tsv"):
        with open(".cogs/renamed.tsv", "r") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                old = row[0]
                new = row[1]
                path = row[2]
                renamed[old] = {"new": new, "path": path}
    return renamed


def get_sheets():
    """Get the current local sheets in this project from sheet.tsv."""
    sheets = {}
    with open(".cogs/sheet.tsv", "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            title = row["Title"]
            if not title:
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


def maybe_update_fields(headers):
    """Given a list of headers, check if any fields were added or removed and update the field.tsv
    if necessary."""
    fields = get_fields()
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


def set_logging(verbose):
    """Set logging for COGS based on -v/--verbose."""
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


def validate_cogs_project():
    """Validate that there is a valid COGS project in this directory. If not, raise an error."""
    if not os.path.exists(".cogs/") or not os.path.isdir(".cogs/"):
        raise CogsError("A COGS project has not been initialized!")
    for r in required_files:
        if not os.path.exists(f".cogs/{r}") or os.stat(f".cogs/{r}").st_size == 0:
            raise CogsError(f"COGS directory is missing {r}")
