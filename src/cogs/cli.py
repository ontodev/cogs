#!/usr/bin/env python

import sys

import cogs.helpers as helpers
import cogs.init as init
import cogs.delete as delete
import cogs.share as share
import cogs.add as add
import cogs.push as push
import cogs.open as open
import cogs.fetch as fetch

from argparse import ArgumentParser


def version(args):
    """Print COGS version information."""
    v = helpers.get_version()
    print(f"COGS version {v}")
    sys.exit(0)


def main():
    parser = ArgumentParser()
    global_parser = ArgumentParser(add_help=False)
    global_parser.add_argument("-v", "--verbose", help="Print logging", action="store_true")
    subparsers = parser.add_subparsers(required=True, dest="cmd")

    sp = subparsers.add_parser("version", parents=[global_parser])
    sp.set_defaults(func=version)

    # ------------------------------- init -------------------------------
    sp = subparsers.add_parser("init", parents=[global_parser])
    sp.add_argument(
        "-c", "--credentials", required=True, help="Path to service account credentials"
    )
    sp.add_argument("-t", "--title", required=True, help="Title of the project")
    sp.add_argument("-u", "--user", help="Email (user) to share spreadsheet with")
    sp.add_argument(
        "-r", "--role", default="writer", help="Role for specified user (default: owner)",
    )
    sp.add_argument("-U", "--users", help="TSV containing user emails and their roles")
    sp.set_defaults(func=init.run)

    # ------------------------------- delete -------------------------------
    sp = subparsers.add_parser("delete", parents=[global_parser])
    sp.set_defaults(func=delete.run)

    # ------------------------------- share -------------------------------
    sp = subparsers.add_parser("share", parents=[global_parser])
    sp.add_argument("-o", "--owner", help="Email of user to transfer ownership of spreadsheet to")
    sp.add_argument("-w", "--writer", help="Email of user to grant write access to")
    sp.add_argument("-r", "--reader", help="Email of user to grant read access to")
    sp.set_defaults(func=share.run)

    # ------------------------------- add -------------------------------
    sp = subparsers.add_parser("add", parents=[global_parser])
    sp.add_argument("path", help="Path to TSV or CSV to add to COGS project")
    sp.add_argument("-d", "--description", help="Description of sheet to add to spreadsheet")
    sp.set_defaults(func=add.run)

    # ------------------------------- push -------------------------------
    sp = subparsers.add_parser("push", parents=[global_parser])
    sp.set_defaults(func=push.run)

    # ------------------------------- open -------------------------------
    sp = subparsers.add_parser("open", parents=[global_parser])
    sp.set_defaults(func=open.run)

    # ------------------------------- fetch -------------------------------
    sp = subparsers.add_parser("fetch", parents=[global_parser])
    sp.set_defaults(func=fetch.run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
