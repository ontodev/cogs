import csv
import google.auth.exceptions
import gspread
import os
import re

required_files = ["user.tsv", "sheet.tsv", "field.tsv", "config.tsv"]


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
            print(
                "ERROR: Unable to create a Client; "
                f"account for client_email in '{credentials}' cannot be found"
            )
        else:
            print(
                f"ERROR: Unable to create a Client; cannot refresh credentials in '{credentials}'"
            )
            print("CAUSE: " + str(e))


def get_config():
    """Get the configuration for this project as a dict."""
    config = {}
    with open(".cogs/config.tsv", "r") as f:
        reader = csv.reader(f, delimiter="\t", lineterminator="\n")
        for row in reader:
            config[row[0]] = row[1]
    return config


def is_cogs_project():
    """Validate that there is a valid COGS project in this directory."""
    if not os.path.exists(".cogs/") or not os.path.isdir(".cogs/"):
        print("ERROR: A COGS project has not been initialized!")
        return False
    for r in required_files:
        if not os.path.exists(f".cogs/{r}") or os.stat(f".cogs/{r}").st_size == 0:
            print(f"ERROR: COGS directory is missing {r}")
            return False
    return True


def is_email(email):
    """Check if a string matches a general email pattern (user@domain.tld)"""
    return re.match(r"^[-.\w]+@[-\w]+\.[-\w]+$", email)


def is_valid_role(role):
    """Check if a string is a valid role for use with gspread."""
    return role in ["owner", "writer", "reader"]
