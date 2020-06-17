#!/usr/bin/env python

import csv
import gspread
import os
import pkg_resources
import sys

from argparse import ArgumentParser


def validate():
    """Validate that there is a valid COGS project in this directory."""
    if not os.path.exists(".cogs/") or not os.path.isdir(".cogs/"):
        print("ERROR: A COGS project has not been initialized!")
        return False
    for r in reqs:
        if not os.path.exists(f".cogs/{r}") or os.stat(f".cogs/{r}").st_size == 0:
            print(
                f"ERROR: COGS directory is missing {r} - please reinitialize and try again."
            )
            return False
    return True


def create(args):
    """Create a new Google Sheet and add it to existing project."""
    if not validate():
        sys.exit(1)

    gc = gspread.service_account(filename=".cogs/credentials.json")

    # Maybe get emails to share sheet with
    emails = {}
    with open(".cogs/user.tsv") as f:
        next(f)
        for line in f:
            e = line.split("\t")[0].strip()
            role = line.split("\t")[1].strip().lower()
            emails[e] = role

    # Create the sheet and share
    print(f"Creating new sheet: {args.title}")
    sh = gc.create(args.title)
    for e, role in emails.items():
        print(f"Sharing {args.title} with {e}")
        sh.share(e, perm_type="user", role=role)

    # Write details to sheet TSV
    with open(".cogs/sheet.tsv", "a") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        desc = ""
        if args.description:
            desc = args.description
        writer.writerow([sh.id, args.title, desc])


def init(args):
    """Init a new .cogs configuration directory in the current working directory. If one already
    exists, reinit it by rewriting config.tsv and ensuring that sheet.tsv and field.tsv exist."""
    cwd = os.getcwd()
    if not os.path.exists(".cogs"):
        print(f"Initializing COGS configuration in {cwd}/.cogs/")
        os.mkdir(".cogs")
    else:
        print(f"Reinitializing existing COGS configuration in {cwd}/.cogs/")

    # Store COGS configuration
    # If this already exists, it *will* be overwritten
    with open(".cogs/config.tsv", "w") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        v = pkg_resources.require("COGS")[0].version
        writer.writerow(["COGS", "https://github.com/ontodev/cogs"])
        writer.writerow(["COGS Version", v])

    # Store credentials
    with open(args.credentials, "r") as fr:
        with open(".cogs/credentials.json", "w") as fw:
            for line in fr:
                fw.write(line)

    # Init sheet.tsv, table.tsv, field.tsv, and user.tsv
    # If these already exist, they will not be overwritten (unless they are empty)
    if not os.path.exists(".cogs/sheet.tsv") or os.stat(".cogs/sheet.tsv").st_size == 0:
        with open(".cogs/sheet.tsv", "w") as f:
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerow(["Sheet ID", "Sheet Title", "Description"])

    if not os.path.exists(".cogs/table.tsv") or os.stat(".cogs/table.tsv").st_size == 0:
        with open(".cogs/table.tsv", "w") as f:
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerow(
                ["Table ID", "Table Title", "Sheet ID", "Path", "Description"]
            )

    if not os.path.exists(".cogs/field.tsv") or os.stat(".cogs/field.tsv").st_size == 0:
        with open(".cogs/field.tsv", "w") as f:
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerow(["Field", "Label", "Datatype", "Description"])
            writer.writerows(default_fields)

    if not os.path.exists(".cogs/user.tsv") or os.stat(".cogs/user.tsv").st_size == 0:
        with open(".cogs/user.tsv", "w") as f:
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerow(["User", "Role"])

    # Maybe add users
    if args.user:
        # Default role is owner (all access)
        role = "owner"
        if args.role:
            role = args.role
        with open(".cogs/user.tsv", "a") as f:
            f.write(f"{args.user}\t{role}\n")

    if args.users:
        with open(args.users, "r") as fr:
            emails = fr.read()
            with open(".cogs/user.tsv", "a") as fw:
                fw.write(emails)
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
    sp.add_argument("-u", "--user", help="Email to share all sheets with")
    sp.add_argument(
        "-r", "--role", help="Role for user specified in email (default: writer)"
    )
    sp.add_argument("-U", "--users", help="TSV containing user emails and their roles")
    sp.set_defaults(func=init)

    sp = subparsers.add_parser("create")
    sp.add_argument("-t", "--title", required=True, help="Title of the new spreadsheet")
    sp.add_argument(
        "-d", "--description", help="Description of the contents of this sheet"
    )
    sp.set_defaults(func=create)

    args = parser.parse_args()
    args.func(args)


default_fields = [
    ["sheet", "Sheet", "cogs:sql_id", "The identifier for this sheet"],
    ["label", "Label", "cogs:label", "The label for this row"],
    [
        "file_path",
        "File Path",
        "cogs:file_path",
        "The relative path of the TSV file for this sheet",
    ],
    ["description", "Description", "cogs:text", "A description of this row"],
    ["field", "Field", "cogs:sql_id", "The identifier for this field"],
    ["datatype", "Datatype", "cogs:curie", "The datatype for this row"],
]

reqs = ["credentials.json", "user.tsv", "sheet.tsv", "table.tsv", "config.tsv"]


if __name__ == "__main__":
    main()
