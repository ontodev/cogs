import csv
import google.auth.exceptions
import gspread
import os
import re

from cogs.exceptions import CogsError

required_files = ["sheet.tsv", "field.tsv", "config.tsv"]

required_keys = ["Spreadsheet ID", "Title", "Credentials"]


def get_client(credentials):
    try:
        gc = gspread.service_account(credentials)
        gc.login()
        return gc
    except gspread.exceptions.APIError as e:
        print(f"ERROR: Unable to create a Client from credentials '{credentials}'")
        print(e.response.text)
    except google.auth.exceptions.RefreshError as e:
        if "invalid_grant" in str(e):
            raise CogsError(
                "ERROR: Unable to create a Client; "
                f"account for client_email in '{credentials}' cannot be found"
            )
        else:
            raise CogsError(
                f"ERROR: Unable to create a Client; cannot refresh credentials in '{credentials}'"
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
            raise CogsError(f"ERROR: COGS configuration does not contain key '{r}'")
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
            del row["Title"]
            sheets[title] = row
    return sheets


def is_email(email):
    """Check if a string matches a general email pattern (user@domain.tld)"""
    return re.match(r"^[-.\w]+@[-\w]+\.[-\w]+$", email)


def is_valid_role(role):
    """Check if a string is a valid role for use with gspread."""
    return role in ["writer", "reader"]


def validate_cogs_project():
    """Validate that there is a valid COGS project in this directory. If not, raise an error."""
    if not os.path.exists(".cogs/") or not os.path.isdir(".cogs/"):
        raise CogsError("ERROR: A COGS project has not been initialized!")
    for r in required_files:
        if not os.path.exists(f".cogs/{r}") or os.stat(f".cogs/{r}").st_size == 0:
            raise CogsError(f"ERROR: COGS directory is missing {r}")
