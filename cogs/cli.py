#!/usr/bin/env python

import cogs.add as add
import cogs.apply as apply
import cogs.delete as delete
import cogs.diff as diff
import cogs.fetch as fetch
import cogs.helpers as helpers
import cogs.init as init
import cogs.ls as ls
import cogs.mv as mv
import cogs.open as open
import cogs.pull as pull
import cogs.push as push
import cogs.rm as rm
import cogs.share as share
import cogs.status as status
import cogs.validate as validate

from argparse import ArgumentParser


def usage():
    return f"""cogs [command] [options] <arguments>
commands:
  add       {add.msg()}
  apply     {apply.msg()}
  delete    {delete.msg()}
  diff      {diff.msg()}
  fetch     {fetch.msg()}
  init      {init.msg()}
  ls        {ls.msg()}
  mv        {mv.msg()}
  open      {open.msg()}
  pull      {pull.msg()}
  push      {push.msg()}
  rm        {rm.msg()}
  share     {share.msg()}
  status    {status.msg()}
  validate  {validate.msg()}
  version   Print the COGS version"""


def version(args):
    """Print COGS version information."""
    v = helpers.get_version()
    print(f"COGS version {v}")


def main():
    parser = ArgumentParser(usage=usage())
    global_parser = ArgumentParser(add_help=False)
    global_parser.add_argument(
        "-v", "--verbose", help="Print logging", action="store_true"
    )
    subparsers = parser.add_subparsers(required=True, dest="cmd")

    sp = subparsers.add_parser("version", parents=[global_parser])
    sp.set_defaults(func=version)

    # ------------------------------- add -------------------------------
    sp = subparsers.add_parser(
        "add",
        parents=[global_parser],
        description=add.msg(),
        usage="cogs add PATH [-d DESCRIPTION -r FREEZE_ROW -c FREEZE_COLUMN]",
    )
    sp.add_argument("path", help="Path to TSV or CSV to add to COGS project")
    sp.add_argument(
        "-d", "--description", help="Description of sheet to add to spreadsheet"
    )
    sp.add_argument(
        "-r", "--freeze-row", help="Row number to freeze up to", default="0"
    )
    sp.add_argument(
        "-c", "--freeze-column", help="Column number to freeze up to", default="0"
    )
    sp.set_defaults(func=add.run)

    # ------------------------------- apply -------------------------------
    sp = subparsers.add_parser(
        "apply",
        parents=[global_parser],
        description=apply.msg(),
        usage="cogs apply [PATH ...]",
    )
    sp.add_argument(
        "paths",
        nargs="*",
        default=None,
        help="Path(s) to ROBOT standardized problems table",
    )
    sp.set_defaults(func=apply.run)

    # ------------------------------- delete -------------------------------
    sp = subparsers.add_parser(
        "delete",
        parents=[global_parser],
        description=delete.msg(),
        usage="cogs delete [-f]",
    )
    sp.set_defaults(func=delete.run)
    sp.add_argument(
        "-f", "--force", action="store_true", help="Delete without confirming"
    )

    # ------------------------------- diff -------------------------------
    sp = subparsers.add_parser(
        "diff",
        parents=[global_parser],
        description=diff.msg(),
        usage="cogs diff [PATH ...]",
    )
    sp.set_defaults(func=diff.run)
    sp.add_argument("paths", nargs="*", help="Paths to local sheets to diff")

    # ------------------------------- fetch -------------------------------
    sp = subparsers.add_parser(
        "fetch", parents=[global_parser], description=fetch.msg(), usage="cogs fetch"
    )
    sp.set_defaults(func=fetch.run)

    # ------------------------------- init -------------------------------
    sp = subparsers.add_parser(
        "init",
        parents=[global_parser],
        description=init.msg(),
        usage="cogs init -c CREDENTIALS -t TITLE [-u USER [-r ROLE]] [-U USERS]",
    )
    sp.add_argument("-c", "--credentials", help="Path to service account credentials")
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

    # ------------------------------- ls -------------------------------
    sp = subparsers.add_parser(
        "ls", parents=[global_parser], description=ls.msg(), usage="cogs ls"
    )
    sp.set_defaults(func=ls.run)

    # ------------------------------- mv -------------------------------
    sp = subparsers.add_parser(
        "mv",
        parents=[global_parser],
        description=mv.msg(),
        usage="cogs mv PATH NEW_PATH",
    )
    sp.add_argument("path", help="Path of local sheet to move")
    sp.add_argument("new_path", help="New path for local sheet")
    sp.set_defaults(func=mv.run)

    # ------------------------------- open -------------------------------
    sp = subparsers.add_parser(
        "open", parents=[global_parser], description=open.msg(), usage="cogs open"
    )
    sp.set_defaults(func=open.run)

    # ------------------------------- pull -------------------------------
    sp = subparsers.add_parser(
        "pull", parents=[global_parser], description=pull.msg(), usage="cogs pull"
    )
    sp.set_defaults(func=pull.run)

    # ------------------------------- push -------------------------------
    sp = subparsers.add_parser(
        "push", parents=[global_parser], description=push.msg(), usage="cogs push"
    )
    sp.set_defaults(func=push.run)

    # -------------------------------- rm --------------------------------
    sp = subparsers.add_parser(
        "rm",
        parents=[global_parser],
        description=rm.msg(),
        usage="cogs rm PATH [PATH ...]",
    )
    sp.add_argument(
        "paths", help="Path(s) to TSV or CSV to remove from COGS project", nargs="+"
    )
    sp.set_defaults(func=rm.run)

    # ------------------------------- share -------------------------------
    sp = subparsers.add_parser(
        "share",
        parents=[global_parser],
        description=share.msg(),
        usage="cogs share [-o OWNER] [-w WRITER] [-r READER]",
    )
    sp.add_argument(
        "-o", "--owner", help="Email of user to transfer ownership of spreadsheet to"
    )
    sp.add_argument("-w", "--writer", help="Email of user to grant write access to")
    sp.add_argument("-r", "--reader", help="Email of user to grant read access to")
    sp.set_defaults(func=share.run)

    # -------------------------------- status --------------------------------
    sp = subparsers.add_parser(
        "status",
        parents=[global_parser],
        description=status.msg(),
        usage="cogs status",
    )
    sp.set_defaults(func=status.run)

    # -------------------------------- validate --------------------------------
    sp = subparsers.add_parser(
        "validate",
        parents=[global_parser],
        description=validate.msg(),
        usage="cogs validate -s SHEET -r RANGE -c CONDITION -v VALUE",
    )
    sp.add_argument("-a", "--apply", help="Path to table of data validation rules to add")
    sp.add_argument("-s", "--sheet", help="Sheet name to add data validation to")
    sp.add_argument("-r", "--range", help="Range to apply data validation to")
    sp.add_argument("-c", "--condition", help="Condition type for data validation")
    sp.add_argument("-V", "--value", help="Allowed value(s) for data validation")
    sp.add_argument("-C", "--clear", help="Clear all data validation from a sheet")
    sp.set_defaults(func=validate.run)

    args = parser.parse_args()
    args.func(args)
