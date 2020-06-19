#!/usr/bin/env python

import pkg_resources
import sys

import cogs.init as init

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
        "-r", "--role", default="owner", help="Role for specified user (default: owner)"
    )
    sp.add_argument("-U", "--users", help="TSV containing user emails and their roles")
    sp.set_defaults(func=init.run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
