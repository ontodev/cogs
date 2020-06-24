#!/usr/bin/env python

import pkg_resources
import sys

import cogs.init as init
import cogs.delete as delete
import cogs.share as share

from argparse import ArgumentParser


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
    sp.add_argument("-u", "--user", help="Email (user) to share all sheets with")
    sp.add_argument(
        "-r", "--role", default="writer", help="Role for specified user (default: owner)"
    )
    sp.add_argument("-U", "--users", help="TSV containing user emails and their roles")
    sp.set_defaults(func=init.run)

    sp = subparsers.add_parser("delete")
    sp.set_defaults(func=delete.run)

    sp = subparsers.add_parser("share")
    sp.add_argument("-o", "--owner", help="Email of user to transfer ownership of Sheet to")
    sp.add_argument("-w", "--writer", help="Email of user to grant write access to")
    sp.add_argument("-r", "--reader", help="Email of user to grant read access to")
    sp.set_defaults(func=share.run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
