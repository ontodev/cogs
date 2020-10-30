#!/usr/bin/env python

import logging
import os
import sys
import tabulate

import cogs.add as add
import cogs.apply as apply
import cogs.clear as clear
import cogs.connect as connect
import cogs.delete as delete
import cogs.diff as diff
import cogs.fetch as fetch
import cogs.helpers as helpers
import cogs.init as init
import cogs.ls as ls
import cogs.mv as mv
import cogs.pull as pull
import cogs.push as push
import cogs.rm as rm
import cogs.share as share
import cogs.status as status

from argparse import ArgumentParser
from .exceptions import CogsError


add_msg = "Add a table (TSV or CSV) to the project"
apply_msg = "Apply a table to the spreadsheet"
clear_msg = "Clear formatting, notes, or data validation rules from one or more sheets"
connect_msg = "Initialize a new COGS project by connecting an existing Google Sheet"
delete_msg = "Delete the Google spreadsheet and COGS configuration"
diff_msg = "Show detailed changes between local & remote sheets"
fetch_msg = "Fetch remote versions of sheets"
init_msg = "Init a new COGS project"
ls_msg = "Show all tracked sheets"
mv_msg = "Move a local sheet to a new path"
open_msg = "Display the Spreadsheet URL"
pull_msg = "Copy fetched sheets to their local paths"
push_msg = "Push local sheets to the spreadsheet"
rm_msg = "Remove a table (TSV or CSV) from the project"
share_msg = "Share the spreadsheet with a user"
status_msg = "Summarize changes between local and fetched sheets"


def usage():
    return f"""cogs [command] [options] <arguments>
commands:
  add       {add_msg}
  apply     {apply_msg}
  connect   {connect_msg}
  clear     {clear_msg}
  delete    {delete_msg}
  diff      {diff_msg}
  fetch     {fetch_msg}
  init      {init_msg}
  ls        {ls_msg}
  mv        {mv_msg}
  open      {open_msg}
  pull      {pull_msg}
  push      {push_msg}
  rm        {rm_msg}
  share     {share_msg}
  status    {status_msg}
  version   Print the COGS version"""


def main():
    parser = ArgumentParser(usage=usage())
    global_parser = ArgumentParser(add_help=False)
    global_parser.add_argument("-v", "--verbose", help="Print logging", action="store_true")
    subparsers = parser.add_subparsers(required=True, dest="cmd")

    sp = subparsers.add_parser("version", parents=[global_parser])
    sp.set_defaults(func=version)

    # ------------------------------- add -------------------------------
    sp = subparsers.add_parser(
        "add",
        parents=[global_parser],
        description=add_msg,
        usage="cogs add PATH [-t TITLE -d DESCRIPTION -r FREEZE_ROW -c FREEZE_COLUMN]",
    )
    sp.add_argument("path", help="Path to TSV or CSV to add to COGS project")
    sp.add_argument("-t", "--title", help="Title of the sheet")
    sp.add_argument("-d", "--description", help="Description of sheet to add to spreadsheet")
    sp.add_argument("-r", "--freeze-row", help="Row number to freeze up to", default="0")
    sp.add_argument("-c", "--freeze-column", help="Column number to freeze up to", default="0")
    sp.set_defaults(func=run_add)

    # ------------------------------- apply -------------------------------
    sp = subparsers.add_parser(
        "apply", parents=[global_parser], description=apply_msg, usage="cogs apply [PATH ...]",
    )
    sp.add_argument(
        "paths", nargs="*", default=None, help="Path(s) to table(s) to apply",
    )
    sp.set_defaults(func=run_apply)

    # ------------------------------- clear -------------------------------
    sp = subparsers.add_parser(
        "clear",
        parents=[global_parser],
        description=clear_msg,
        usage="cogs clear KEYWORD [SHEET ...]",
    )
    sp.set_defaults(func=run_clear)
    sp.add_argument("keyword", help="Specify what to clear from the sheet(s)")
    sp.add_argument("sheets", nargs="*", help="Titles of sheets to clear from", default=[])

    # ------------------------------- connect -------------------------------
    sp = subparsers.add_parser(
        "connect",
        parents=[global_parser],
        description=connect_msg,
        usage="cogs connect -k KEY [-c CREDENTIALS]",
    )
    sp.set_defaults(func=run_connect)
    sp.add_argument("-k", "--key", help="Existing Google Sheet key to connect")
    sp.add_argument("-c", "--credentials", help="Path to service account credentials")
    sp.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Connect sheet without displaying sharing instruction",
    )

    # ------------------------------- delete -------------------------------
    sp = subparsers.add_parser(
        "delete", parents=[global_parser], description=delete_msg, usage="cogs delete [-f]",
    )
    sp.set_defaults(func=run_delete)
    sp.add_argument("-f", "--force", action="store_true", help="Delete without confirming")

    # ------------------------------- diff -------------------------------
    sp = subparsers.add_parser(
        "diff", parents=[global_parser], description=diff_msg, usage="cogs diff [PATH ...]",
    )
    sp.set_defaults(func=run_diff)
    sp.add_argument("paths", nargs="*", help="Paths to local sheets to diff")

    # ------------------------------- fetch -------------------------------
    sp = subparsers.add_parser(
        "fetch", parents=[global_parser], description=fetch_msg, usage="cogs fetch"
    )
    sp.set_defaults(func=run_fetch)

    # ------------------------------- init -------------------------------
    sp = subparsers.add_parser(
        "init",
        parents=[global_parser],
        description=init_msg,
        usage="cogs init -c CREDENTIALS -t TITLE [-u USER [-r ROLE]] [-U USERS]",
    )
    sp.add_argument("-c", "--credentials", help="Path to service account credentials")
    sp.add_argument("-t", "--title", required=True, help="Title of the project")
    sp.add_argument("-u", "--user", help="Email (user) to share spreadsheet with")
    sp.add_argument(
        "-r", "--role", default="writer", help="Role for specified user (default: owner)",
    )
    sp.add_argument("-U", "--users", help="TSV containing user emails and their roles")
    sp.set_defaults(func=run_init)

    # ------------------------------- ls -------------------------------
    sp = subparsers.add_parser("ls", parents=[global_parser], description=ls_msg, usage="cogs ls")
    sp.set_defaults(func=run_ls)

    # ------------------------------- mv -------------------------------
    sp = subparsers.add_parser(
        "mv", parents=[global_parser], description=mv_msg, usage="cogs mv PATH NEW_PATH",
    )
    sp.add_argument("path", help="Path of local sheet to move")
    sp.add_argument("new_path", help="New path for local sheet")
    sp.add_argument(
        "-f",
        "--force",
        help="Overwrite existing files at the new-path location without confirming",
        action="store_true",
    )
    sp.set_defaults(func=run_mv)

    # ------------------------------- open -------------------------------
    sp = subparsers.add_parser(
        "open", parents=[global_parser], description=open_msg, usage="cogs open",
    )
    sp.set_defaults(func=run_open)

    # ------------------------------- pull -------------------------------
    sp = subparsers.add_parser(
        "pull", parents=[global_parser], description=pull_msg, usage="cogs pull"
    )
    sp.set_defaults(func=run_pull)

    # ------------------------------- push -------------------------------
    sp = subparsers.add_parser(
        "push", parents=[global_parser], description=push_msg, usage="cogs push"
    )
    sp.set_defaults(func=run_push)

    # -------------------------------- rm --------------------------------
    sp = subparsers.add_parser(
        "rm", parents=[global_parser], description=rm_msg, usage="cogs rm PATH [PATH ...]",
    )
    sp.add_argument("paths", help="Path(s) to TSV or CSV to remove from COGS project", nargs="+")
    sp.set_defaults(func=run_rm)

    # ------------------------------- share -------------------------------
    sp = subparsers.add_parser(
        "share",
        parents=[global_parser],
        description=share_msg,
        usage="cogs share [-o OWNER] [-w WRITER] [-r READER]",
    )
    sp.add_argument("-o", "--owner", help="Email of user to transfer ownership of spreadsheet to")
    sp.add_argument("-w", "--writer", help="Email of user to grant write access to")
    sp.add_argument("-r", "--reader", help="Email of user to grant read access to")
    sp.add_argument(
        "-f", "--force", action="store_true", help="Transfer ownership without confirming"
    )
    sp.set_defaults(func=run_share)

    # -------------------------------- status --------------------------------
    sp = subparsers.add_parser(
        "status", parents=[global_parser], description=status_msg, usage="cogs status",
    )
    sp.set_defaults(func=run_status)

    args = parser.parse_args()
    args.func(args)


def run_add(args):
    """Wrapper for add function."""
    try:
        add(
            args.path,
            title=args.title,
            description=args.description,
            freeze_row=args.freeze_row,
            freeze_column=args.freeze_column,
            verbose=args.verbose,
        )
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)


def run_apply(args):
    """Wrapper for apply function."""
    try:
        apply(args.paths, verbose=args.verbose)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)


def run_clear(args):
    """Wrapper for clear function."""
    try:
        clear(args.keyword, on_sheets=args.sheets, verbose=args.verbose)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)


def run_connect(args):
    """Wrapper for connect function."""
    try:
        success = connect(
            args.keyword, credentials=args.credentials, force=args.force, verbose=args.verbose
        )
        if not success:
            # Exit with error status without deleting COGS directory
            sys.exit(1)
    except CogsError as e:
        # Exit with error status AND delete directory
        logging.critical(str(e))
        sys.exit(1)


def run_delete(args):
    """Wrapper for delete function."""
    try:
        if not args.force:
            resp = input(
                "WARNING: This task will permanently destroy the spreadsheet and all COGS data.\n"
                "         Do you wish to proceed? [y/n]\n"
            )
            if resp.lower().strip() != "y":
                logging.warning("'delete' operation stopped")
                sys.exit(0)
        delete(verbose=args.verbose)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)


def run_diff(args):
    """Wrapper for diff function."""
    try:
        has_diff = diff(paths=args.paths, verbose=args.verbose)
        if not has_diff:
            print("Local sheets are up to date with remote sheets (nothing to push or pull).\n")
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)


def run_fetch(args):
    """Wrapper for fetch function."""
    try:
        fetch(verbose=args.verbose)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)


def run_init(args):
    """Wrapper for init function."""
    try:
        success = init(
            args.title,
            user=args.user,
            role=args.role,
            users_file=args.users,
            credentials=args.credentials,
            verbose=args.verbose,
        )
        if not success:
            # Exit with error status without deleting COGS directory
            sys.exit(1)
    except CogsError as e:
        # Exit with error status AND delete new COGS directory
        logging.critical(str(e))
        if os.path.exists(".cogs"):
            os.rmdir(".cogs")
        sys.exit(1)


def run_ls(args):
    """Wrapper for ls function."""
    try:
        sheet_details = ls(verbose=args.verbose)
        print(tabulate.tabulate(sheet_details, tablefmt="plain"))
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)


def run_mv(args):
    """Wrapper for mv function."""
    try:
        mv(args.path, args.new_path, force=args.force, verbose=args.verbose)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)


def run_open(args):
    try:
        print(helpers.get_sheet_url())
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)


def run_pull(args):
    """Wrapper for pull function."""
    try:
        pull(verbose=args.verbose)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)


def run_push(args):
    """Wrapper for push function."""
    try:
        push(verbose=args.verbose)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)


def run_rm(args):
    """Wrapper for rm function."""
    try:
        rm(args.paths, verbose=args.verbose)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)


def run_share(args):
    """Wrapper for share function."""
    try:
        if args.owner:
            transfer = True
            if not args.force:
                resp = input(
                    f"WARNING: Transferring ownership to {args.owner} will prevent COGS from "
                    f"performing admin actions on the Spreadsheet. Do you wish to proceed? [y/n]\n"
                )
                if resp.lower().strip() != "y":
                    print(f"Ownership of Spreadsheet will not be transferred.")
                    transfer = False
            if transfer:
                share(args.owner, "owner", verbose=args.verbose)
        if args.writer:
            share(args.writer, "writer", verbose=args.verbose)
        if args.reader:
            share(args.reader, "reader", verbose=args.verbose)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)


def run_status(args):
    """Wrapper for status function."""
    try:
        changes = status(verbose=args.verbose)
        if not changes:
            print("Local sheets are up to date with remote sheets (nothing to push or pull).\n")
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)


def version(args):
    """Print COGS version information."""
    v = helpers.get_version()
    print(f"COGS version {v}")
