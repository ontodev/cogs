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


def get_version():
    try:
        version = pkg_resources.require("COGS")[0].version
    except pkg_resources.DistributionNotFound:
        version = "developer-version"
    return version


def get_client(credentials):
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


def is_email(email):
    """Check if a string matches a general email pattern (user@domain.tld)"""
    return re.match(r"^[-.\w]+@[-\w]+\.[-\w]+$", email)


def is_valid_role(role):
    """Check if a string is a valid role for use with gspread."""
    return role in ["writer", "reader"]


def set_logging(verbose):
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.ERROR, format="%(levelname)s: %(message)s")


def validate_cogs_project():
    """Validate that there is a valid COGS project in this directory. If not, raise an error."""
    if not os.path.exists(".cogs/") or not os.path.isdir(".cogs/"):
        raise CogsError("A COGS project has not been initialized!")
    for r in required_files:
        if not os.path.exists(f".cogs/{r}") or os.stat(f".cogs/{r}").st_size == 0:
            raise CogsError(f"COGS directory is missing {r}")
