#!/usr/bin/env python

import csv
import os
import pkg_resources
import sys

from argparse import ArgumentParser


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
        writer = csv.writer(f, delimiter='\t', lineterminator='\n')
        v = pkg_resources.require("COGS")[0].version
        writer.writerow(["COGS", "https://github.com/ontodev/cogs"])
        writer.writerow(["COGS Version", v])

    # Init sheet.tsv and field.tsv
    # If these already exist, they will not be overwritten (unless they are empty)
    if not os.path.exists(".cogs/sheet.tsv") or os.stat(".cogs/sheet.tsv").st_size == 0:
        with open(".cogs/sheet.tsv", "w") as f:
            writer = csv.writer(f, delimiter='\t', lineterminator='\n')
            writer.writerow(["Sheet", "Label", "File Path", "Description"])

    if not os.path.exists(".cogs/field.tsv") or os.stat(".cogs/field.tsv").st_size == 0:
        with open(".cogs/field.tsv", "w") as f:
            writer = csv.writer(f, delimiter='\t', lineterminator='\n')
            writer.writerow(["Field", "Label", "Datatype", "Description"])
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
    sp.set_defaults(func=init)

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


if __name__ == "__main__":
    main()
