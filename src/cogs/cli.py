#!/usr/bin/env python

import pkg_resources
import sys

import cogs.init as init
import cogs.delete as delete
import cogs.share as share
import cogs.add as add
import cogs.push as push
import cogs.open as open

from argparse import ArgumentParser


def get_version():
    try:
        version = pkg_resources.require("COGS")[0].version
    except pkg_resources.DistributionNotFound:
        version = "developer-version"
    return version


def version(args):
    """Print COGS version information."""
    v = get_version()
    print(f"COGS version {v}")
    sys.exit(0)


def main():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(required=True, dest="cmd")

    sp = subparsers.add_parser("version")
    sp.set_defaults(func=version)

    # ------------------------------- init -------------------------------
    sp = subparsers.add_parser("init")
    sp.add_argument(
        "-c", "--credentials", required=True, help="Path to service account credentials"
    )
    sp.add_argument("-t", "--title", required=True, help="Title of the project")
    sp.add_argument("-u", "--user", help="Email (user) to share spreadsheet with")
    sp.add_argument(
        "-r",
        "--role",
        default="writer",
        help="Role for specified user (default: owner)",
    )
    sp.add_argument("-U", "--users", help="TSV containing user emails and their roles")
    sp.set_defaults(func=init.run)

    # ------------------------------- delete -------------------------------
    sp = subparsers.add_parser("delete")
    sp.set_defaults(func=delete.run)

    # ------------------------------- share -------------------------------
    sp = subparsers.add_parser("share")
    sp.add_argument(
        "-o", "--owner", help="Email of user to transfer ownership of spreadsheet to"
    )
    sp.add_argument("-w", "--writer", help="Email of user to grant write access to")
    sp.add_argument("-r", "--reader", help="Email of user to grant read access to")
    sp.set_defaults(func=share.run)

    # ------------------------------- add -------------------------------
    sp = subparsers.add_parser("add")
    sp.add_argument("path", help="Path to TSV or CSV to add to COGS project")
    sp.add_argument("-d", "--description", help="Description of sheet to add to spreadsheet")
    sp.set_defaults(func=add.run)

    # ------------------------------- push -------------------------------
    sp = subparsers.add_parser("push")
    sp.set_defaults(func=push.run)

    # ------------------------------- open -------------------------------
    sp = subparsers.add_parser("open")
    sp.set_defaults(func=open.run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
