#!/usr/bin/env python

import csv
import gspread
import os
import pkg_resources
import sys

from argparse import ArgumentParser


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
    for r in reqs:
        if not os.path.exists(f".cogs/{r}") or os.stat(f".cogs/{r}").st_size == 0:
            print(f"ERROR: COGS directory is missing {r}")
            return False
    return True


def init(args):
    """Init a new .cogs configuration directory in the current working directory. If one already
    exists, display an error message."""
    cwd = os.getcwd()
    if os.path.exists(".cogs"):
        print(f"ERROR: COGS project already exists in {cwd}/.cogs/")
        sys.exit(1)

    print(f"Initializing COGS project '{args.title}' in {cwd}/.cogs/")
    os.mkdir(".cogs")

    # Create the sheet for this project
    gc = gspread.service_account(args.credentials)
    sh = gc.create(args.title)

    # Maybe get users and share new sheet with them
    users = {}
    if args.user:
        # Default role is owner
        role = "owner"
        if args.role:
            role = args.role
        users[args.user] = role
    if args.users:
        with open(args.users, "r") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                users[row[0]] = row[1]
    for email, role in users.items():
        sh.share(email, perm_type="user", role=role)

    # Store COGS configuration
    with open(".cogs/config.tsv", "w") as f:
        writer = csv.DictWriter(
            f, delimiter="\t", lineterminator="\n", fieldnames=["Key", "Value"]
        )
        v = pkg_resources.require("COGS")[0].version
        writer.writerow({"Key": "COGS", "Value": "https://github.com/ontodev/cogs"})
        writer.writerow({"Key": "COGS Version", "Value": v})
        writer.writerow({"Key": "Credentials", "Value": args.credentials})
        writer.writerow({"Key": "Title", "Value": args.title})
        writer.writerow({"Key": "ID", "Value": sh.id})

    # sheet.tsv contains table (tab) details from the Google Sheet
    with open(".cogs/sheet.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["ID", "Title", "Path", "Description"],
        )
        writer.writeheader()

    # field.tsv contains the field headers used in the sheets
    with open(".cogs/field.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["Field", "Label", "Datatype", "Description"],
        )
        writer.writeheader()
        writer.writerows(default_fields)
    sys.exit(0)


def version(args):
    """Print COGS version information."""
    v = pkg_resources.require("COGS")[0].version
    print(f"COGS version {v}")
    sys.exit(0)


def main():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(required=True, dest="cmd")

    sp = subparsers.add_parser("version")
    sp.set_defaults(func=version)

    sp = subparsers.add_parser("init")
    sp.add_argument(
        "-c", "--credentials", required=True, help="Path to service account credentials"
    )
    sp.add_argument("-t", "--title", required=True, help="Title of the project")
    sp.add_argument("-u", "--user", help="Email to share all sheets with")
    sp.add_argument(
        "-r", "--role", help="Role for user specified in email (default: writer)"
    )
    sp.add_argument("-U", "--users", help="TSV containing user emails and their roles")
    sp.set_defaults(func=init)

    args = parser.parse_args()
    args.func(args)


default_fields = [
    {
        "Field": "sheet",
        "Label": "Sheet",
        "Datatype": "cogs:sql_id",
        "Description": "The identifier for this sheet",
    },
    {
        "Field": "label",
        "Label": "Label",
        "Datatype": "cogs:label",
        "Description": "The label for this row",
    },
    {
        "Field": "file_path",
        "Label": "File Path",
        "Datatype": "cogs:file_path",
        "Description": "The relative path of the TSV file for this sheet",
    },
    {
        "Field": "description",
        "Label": "Description",
        "Datatype": "cogs:text",
        "Description": "A description of this row",
    },
    {
        "Field": "field",
        "Label": "Field",
        "Datatype": "cogs:sql_id",
        "Description": "The identifier for this field",
    },
    {
        "Field": "datatype",
        "Label": "Datatype",
        "Datatype": "cogs:curie",
        "Description": "The datatype for this row",
    },
]

reqs = ["user.tsv", "sheet.tsv", "field.tsv", "config.tsv"]


if __name__ == "__main__":
    main()
