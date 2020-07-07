import logging
import os
import sys
import termcolor

from cogs.exceptions import CogsError
from cogs.helpers import (
    get_diff,
    get_client,
    get_config,
    get_sheets,
    set_logging,
    validate_cogs_project,
)


def get_changes(tracked_sheets):
    """Get sets of changes between local and remote sheets."""
    # Get all cached sheet titles that are not COGS defaults
    cached_sheet_titles = []
    for f in os.listdir(".cogs"):
        if f not in ["user.tsv", "sheet.tsv", "field.tsv", "config.tsv"]:
            cached_sheet_titles.append(f.split(".")[0])

    # Get all tracked sheet titles
    tracked_sheet_titles = list(tracked_sheets.keys())

    # Get tracked titles that have local copies
    local_sheet_titles = []

    # And tracked titles that have been pushed to remote (given ID)
    pushed_local_sheet_titles = []

    for sheet_title, details in tracked_sheets.items():
        local_sheet = details["Path"]
        sid = details["ID"].strip()
        if sid != "":
            pushed_local_sheet_titles.append(sheet_title)
        if os.path.exists(local_sheet):
            local_sheet_titles.append(sheet_title)

    removed_remote = []
    added_local = []
    removed_local = []
    added_remote = []
    diffs = {}

    all_sheets = set(local_sheet_titles + tracked_sheet_titles)
    for sheet_title in all_sheets:
        # Is the sheet cached in .cogs?
        cached = False
        if sheet_title in cached_sheet_titles:
            cached = True

        # Is the sheet tracked in sheet.tsv?
        tracked = False
        if sheet_title in tracked_sheet_titles:
            tracked = True

        # Does the sheet exist at its local path?
        local = False
        if sheet_title in local_sheet_titles:
            local = True

        # Does the sheet have an ID (meaning it has been pushed)?
        local_pushed = False
        if sheet_title in pushed_local_sheet_titles:
            local_pushed = True

        if tracked and local and local_pushed and not cached:
            # Removed remotely and not yet pulled
            removed_remote.append(sheet_title)
        elif tracked and local and not local_pushed and not cached:
            # Added locally and not yet pushed
            added_local.append(sheet_title)
        elif not tracked and not local and not cached:
            # Removed locally and not yet pushed
            removed_local.append(sheet_title)
        elif tracked and not local and cached:
            # Added remotely and not yet pulled
            added_remote.append(sheet_title)
        else:
            # Exists in both - run diff
            local_path = tracked_sheets[sheet_title]["Path"]
            remote_path = f".cogs/{sheet_title}.tsv"
            diff = get_diff(local_path, remote_path)
            if len(diff) > 1:
                added_lines = 0
                removed_lines = 0
                changed_lines = 0
                added_cols = 0
                removed_cols = 0
                for idx in range(0, len(diff)):
                    d = diff[idx]
                    if idx == 0 and d[0] == "!":
                        # Get changed columns
                        for h in d:
                            if h == "+++":
                                added_cols += 1
                            elif h == "---":
                                removed_cols += 1
                        continue
                    if d[0] == "---":
                        removed_lines += 1
                    elif d[0] == "+++":
                        added_lines += 1
                    elif d[0] == "->":
                        changed_lines += 1
                diffs[sheet_title] = {
                    "added_cols": added_cols,
                    "removed_cols": removed_cols,
                    "added_lines": added_lines,
                    "removed_lines": removed_lines,
                    "changed_lines": changed_lines,
                }

    return diffs, added_local, added_remote, removed_local, removed_remote


def status(args):
    """Print the status of local sheets vs. remote sheets."""
    set_logging(args.verbose)
    validate_cogs_project()

    # Get the sets of changes
    tracked_sheets = get_sheets()
    diffs, added_local, added_remote, removed_local, removed_remote = get_changes(tracked_sheets)

    # Check to see if we have any changes
    all_changes = set(
        list(diffs.keys()) + added_local + added_remote + removed_local + removed_remote
    )
    if len(all_changes) == 0:
        print("Local sheets are up to date with remote spreadsheet.")
        return

    # Print various changes
    if len(diffs) > 0:
        print(termcolor.colored("\nChanged:", attrs=["bold"]))
        print(
            "  (use `cogs pull` to sync local with remote version)\n  "
            "(use `cogs push` to sync remote with local version)"
        )
        for sheet_title, diff in diffs.items():
            path = tracked_sheets[sheet_title]["Path"]
            print(termcolor.colored(f"\t{sheet_title} ({path})", "cyan"))
            added_lines = diff["added_lines"]
            removed_lines = diff["removed_lines"]
            changed_lines = diff["changed_lines"]
            added_cols = diff["added_cols"]
            removed_cols = diff["removed_cols"]
            if added_cols:
                print(termcolor.colored(f"\t  {added_cols} added column(s)", "green"))
            if added_lines:
                print(termcolor.colored(f"\t  {added_lines} added line(s)", "green"))
            if removed_cols:
                print(termcolor.colored(f"\t  {removed_cols} removed column(s)", "red"))
            if removed_lines:
                print(termcolor.colored(f"\t  {removed_lines} removed line(s)", "red"))
            if changed_lines:
                print(termcolor.colored(f"\t  {changed_lines} changed line(s)", "cyan"))
    if len(added_local) > 0:
        print(termcolor.colored("\nAdded locally:", attrs=["bold"]))
        print(
            "  (use `cogs push` to add to remote spreadsheet)\n  "
            "(use `cogs rm [path]` to remove from tracked sheets)"
        )
        for sheet_title in added_local:
            path = tracked_sheets[sheet_title]["Path"]
            print(termcolor.colored(f"\t{sheet_title} ({path})", "green"))
    if len(added_remote) > 0:
        print(termcolor.colored("\nAdded remotely:", attrs=["bold"]))
        print(
            "  (use `cogs pull` to add to local sheets)\n  "
            "(use `cogs rm [path]` to remove from tracked sheets)"
        )
        for sheet_title in added_remote:
            path = tracked_sheets[sheet_title]["Path"]
            print(termcolor.colored(f"\t{sheet_title} ({path})", "green"))
    if len(removed_local) > 0:
        print(termcolor.colored("\nRemoved locally:", attrs=["bold"]))
        print(
            "  (use `cogs push` to remove from remote spreadsheet)\n  "
            "(use `cogs add [path]` to re-add to tracked sheets)"
        )
        for sheet_title in removed_local:
            print(termcolor.colored(f"\t{sheet_title}", "red"))
    if len(removed_remote) > 0:
        print(termcolor.colored("\nRemoved remotely:", attrs=["bold"]))
        print(
            "  (use `cogs pull` to remove from local sheets)\n  "
            "(use `cogs push` to re-add to remote spreadsheet)"
        )
        for sheet_title in removed_remote:
            path = tracked_sheets[sheet_title]["Path"]
            print(termcolor.colored(f"\t{sheet_title} ({path})", "red"))
    print("")


def run(args):
    """Wrapper for status function."""
    try:
        status(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
