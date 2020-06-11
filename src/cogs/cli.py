#!/usr/bin/env python

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
        v = pkg_resources.require("COGS")[0].version
        f.write("COGS\thttps://github.com/ontodev/cogs\n")
        f.write(f"COGS Version\t{v}\n")

    # Init sheet.tsv and field.tsv
    # If these already exist, they will not be overwritten
    open(".cogs/sheet.tsv", "a").close()
    open(".cogs/field.tsv", "a").close()
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


if __name__ == "__main__":
    main()
