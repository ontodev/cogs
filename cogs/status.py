import os
import re
import termcolor

from cogs.helpers import (
    get_cached_sheets,
    get_diff,
    set_logging,
    validate_cogs_project,
    get_tracked_sheets,
    get_renamed_sheets,
)


def get_changes(cogs_dir, tracked_sheets, renamed):
    """Get sets of changes between local and remote sheets. Return dict in format:
    {"diffs": diffs built from daff (list of dicts),
     "added local": added_local (sheet names),
     "added remote": added_remote (sheet names),
     "removed local": removed_local (sheet names),
     "removed remote": removed_remote (sheet names)
    }"""
    # Get all cached sheet titles that are not COGS defaults
    cached_sheet_titles = get_cached_sheets(cogs_dir)
    tracked_cached = []

    # Get all tracked sheet titles
    tracked_sheet_titles = list(tracked_sheets.keys())
    for st in tracked_sheet_titles:
        path_name = re.sub(r"[^A-Za-z0-9]+", "_", st.lower())
        if path_name in cached_sheet_titles:
            tracked_cached.append(path_name)

    untracked_cached = [x for x in cached_sheet_titles if x not in tracked_cached]

    # Get tracked titles that have local copies
    local_sheet_titles = []

    # And tracked titles that have been pushed to remote (given ID)
    pushed_local_sheet_titles = []

    renamed_remote = {
        old: details for old, details in renamed.items() if details["where"] == "remote"
    }
    new_remote = [details["new"] for details in renamed_remote.values()]

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

    all_sheets = set(tracked_sheet_titles + untracked_cached)
    for sheet_title in all_sheets:
        # Is the sheet cached in .cogs?
        cached = False
        if re.sub(r"[^A-Za-z0-9]+", "_", sheet_title.lower()) in cached_sheet_titles:
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
        elif not tracked and not local and cached and sheet_title not in renamed:
            # Removed locally and not yet pushed
            removed_local.append(sheet_title)
        elif tracked and not local and cached and sheet_title not in new_remote:
            # Added remotely and not yet pulled
            added_remote.append(sheet_title)
        else:
            # Exists in both - run diff
            if sheet_title in renamed:
                sheet_title = renamed[sheet_title]["new"]
            local_path = tracked_sheets[sheet_title]["Path"]
            path_name = re.sub(r"[^A-Za-z0-9]+", "_", sheet_title.lower())
            remote_path = f"{cogs_dir}/tracked/{path_name}.tsv"

            if not os.path.exists(local_path) or not os.path.exists(remote_path):
                # Subject to a rename
                continue

            # Check which version is newer based on file modification
            local_mod = os.path.getmtime(local_path)
            remote_mod = os.path.getmtime(remote_path)
            if remote_mod > local_mod:
                diff = get_diff(remote_path, local_path)
                new_version = "remote"
            else:
                diff = get_diff(local_path, remote_path)
                new_version = "local"

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
                    "new_version": new_version,
                    "added_cols": added_cols,
                    "removed_cols": removed_cols,
                    "added_lines": added_lines,
                    "removed_lines": removed_lines,
                    "changed_lines": changed_lines,
                }

    return {
        "diffs": diffs,
        "added local": added_local,
        "added remote": added_remote,
        "removed local": removed_local,
        "removed remote": removed_remote,
    }


def print_diff(sheet_title, path, diff):
    """Print the diff summary for a sheet."""
    added_lines = diff["added_lines"]
    removed_lines = diff["removed_lines"]
    changed_lines = diff["changed_lines"]
    added_cols = diff["added_cols"]
    removed_cols = diff["removed_cols"]

    print(termcolor.colored(f"\t{sheet_title} ({path})", "cyan"))

    if added_cols and added_lines:
        col = "column"
        if added_cols > 1:
            col = "columns"
        line = "line"
        if added_lines > 1:
            line = "lines"
        print(termcolor.colored(f"\t  + {added_cols} {col}, {added_lines} {line}", "green"))
    elif added_lines:
        line = "line"
        if added_lines > 1:
            line = "lines"
        print(termcolor.colored(f"\t  + {added_lines} {line}", "green"))
    elif added_cols:
        col = "column"
        if added_cols > 1:
            col = "columns"
        print(termcolor.colored(f"\t  + {added_cols} {col}", "green"))

    if removed_cols and removed_lines:
        col = "column"
        if removed_cols > 1:
            col = "columns"
        line = "line"
        if removed_lines > 1:
            line = "lines"
        print(termcolor.colored(f"\t  - {removed_cols} {col}, {removed_lines} {line}", "red"))
    elif removed_cols:
        col = "column"
        if removed_cols > 1:
            col = "columns"
        print(termcolor.colored(f"\t  - {removed_cols} {col}", "red"))
    elif removed_lines:
        line = "line"
        if removed_lines > 1:
            line = "lines"
        print(termcolor.colored(f"\t  - {removed_lines} {line}", "red"))

    if changed_lines:
        line = "line"
        if changed_lines > 1:
            line = "lines"
        print(termcolor.colored(f"\t  -> {changed_lines} changed {line}", "cyan"))


def print_status(changes, renamed, tracked_sheets):
    """Using a dict of changes, print the status of the changed sheets in the project."""
    diffs = changes["diffs"]
    added_local = changes["added local"]
    added_remote = changes["added remote"]
    removed_local = changes["removed local"]
    removed_remote = changes["removed remote"]

    renamed_local = {
        old: details for old, details in renamed.items() if details["where"] == "local"
    }
    renamed_remote = {
        old: details for old, details in renamed.items() if details["where"] == "remote"
    }

    # Print various changes
    if len(renamed_local) > 0:
        print(termcolor.colored("\nRenamed locally:", attrs=["bold"]))
        print("  (use `cogs push` to update in remote spreadsheet)")
        for old, details in renamed.items():
            new = details["new"]
            path = details["path"]
            print(termcolor.colored(f"\t{old} -> {new} ({path})", "cyan"))

    if len(renamed_remote) > 0:
        print(termcolor.colored("\nRenamed remotely:", attrs=["bold"]))
        print("  (use `cogs pull` to sync local with remote version)")
        for old, details in renamed.items():
            new = details["new"]
            path = details["path"]
            print(termcolor.colored(f"\t{old} -> {new} ({path})", "cyan"))

    if len(diffs) > 0:
        changed_local = {
            sheet_title: diff
            for sheet_title, diff in diffs.items()
            if diff["new_version"] == "local"
        }
        changed_remote = {
            sheet_title: diff
            for sheet_title, diff in diffs.items()
            if diff["new_version"] == "remote"
        }
        if len(changed_local) > 0:
            print(termcolor.colored("\nModified locally:", attrs=["bold"]))
            print("  (use `cogs push` to sync remote with local version)")
            for sheet_title, diff in changed_local.items():
                path = tracked_sheets[sheet_title]["Path"]
                print_diff(sheet_title, path, diff)
        if len(changed_remote) > 0:
            print(termcolor.colored("\nModified remotely:", attrs=["bold"]))
            print("  (use `cogs pull` to sync local with remote version)")
            for sheet_title, diff in changed_remote.items():
                path = tracked_sheets[sheet_title]["Path"]
                print_diff(sheet_title, path, diff)

    if len(added_local) > 0:
        print(termcolor.colored("\nAdded locally:", attrs=["bold"]))
        print("  (use `cogs push` to add to remote spreadsheet)\n  ")
        for sheet_title in added_local:
            path = tracked_sheets[sheet_title]["Path"]
            print(termcolor.colored(f"\t{sheet_title} ({path})", "green"))

    if len(added_remote) > 0:
        print(termcolor.colored("\nAdded remotely:", attrs=["bold"]))
        print("  (use `cogs pull` to add to local sheets)")
        for sheet_title in added_remote:
            path = tracked_sheets[sheet_title]["Path"]
            print(termcolor.colored(f"\t{sheet_title} ({path})", "green"))

    if len(removed_local) > 0:
        print(termcolor.colored("\nRemoved locally:", attrs=["bold"]))
        print("  (use `cogs push` to remove from remote spreadsheet)")
        for sheet_title in removed_local:
            print(termcolor.colored(f"\t{sheet_title}", "red"))

    if len(removed_remote) > 0:
        print(termcolor.colored("\nRemoved remotely:", attrs=["bold"]))
        print("  (use `cogs pull` to remove from local sheets)")
        for sheet_title in removed_remote:
            path = tracked_sheets[sheet_title]["Path"]
            print(termcolor.colored(f"\t{sheet_title} ({path})", "red"))
    print("")


def status(use_screen=True, verbose=False):
    """Return a dict containing:
    - changes (dict of new_version, added_cols, removed_cols, added_lines, removed_lines,
      changed_lines built from daff)
    - added local (sheet names)
    - removed local (sheet names)
    - added remote (sheet names)
    - removed remote (sheet names)
    If use_screen, print the status of local sheets vs. remote sheets."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()

    # Get the sets of changes
    tracked_sheets = get_tracked_sheets(cogs_dir)
    renamed = get_renamed_sheets(cogs_dir)
    changes = get_changes(cogs_dir, tracked_sheets, renamed)

    # Get a count of all changes
    change_count = set(
        list(changes["diffs"].keys())
        + changes["added local"]
        + changes["added remote"]
        + changes["removed local"]
        + changes["removed remote"]
    )
    if len(change_count) == 0 and len(renamed) == 0:
        return None

    if use_screen:
        print_status(changes, renamed, tracked_sheets)
    return changes
