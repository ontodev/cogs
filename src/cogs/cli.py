#!/usr/bin/env python

import pkg_resources
import sys

from argparse import ArgumentParser


def version(args):
    v = pkg_resources.require("COGS")[0].version
    print(f"COGS version {v}")
    sys.exit(0)


def main():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(required=True, dest="cmd")

    sp = subparsers.add_parser("version")
    sp.set_defaults(func=version)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
