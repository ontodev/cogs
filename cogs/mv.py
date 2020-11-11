import ntpath
import shutil

from cogs.exceptions import MvError
from cogs.helpers import *


def mv(path, new_path, force=False, verbose=False):
    """Move a local sheet to a new local path. If the file basename changes, the sheet title will
    also change."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()

    if not os.path.exists(path):
        raise MvError(f"{path} does not exist")

    if os.path.exists(path) and os.path.exists(new_path) and not force:
        # Make sure the user knows they are overwriting another file
        i = input(
            f"{path} and {new_path} both exist - "
            f"'mv' will overwrite the contents of {new_path}.\nDo you wish to proceed? [y/n]\n"
        )
        if i.strip().lower() != "y":
            logging.warning("'mv' operation stopped")
            return

    # Get the tracked sheets
    tracked_sheets = get_tracked_sheets(cogs_dir)
    path_to_sheet = {
        os.path.abspath(details["Path"]): sheet_title
        for sheet_title, details in tracked_sheets.items()
    }

    # Make sure the sheet we are moving is tracked and get its (current) title
    cur_path = os.path.abspath(path)
    if cur_path not in path_to_sheet:
        raise MvError(f"{path} is not a tracked sheet")

    # Move the local copy if it exists
    # If it doesn't exist, the user has already moved to the new path
    if os.path.exists(path):
        os.rename(path, new_path)

    # See if the basename (sheet title) changed
    # If so, we need to rename the cached copy
    selected_sheet = path_to_sheet[cur_path]
    new_sheet_title = ntpath.basename(new_path).split(".")[0]
    if selected_sheet != new_sheet_title:
        if os.path.exists(f"{cogs_dir}/tracked/{new_sheet_title}.tsv"):
            # A cached sheet with this name already exists
            existing_path = tracked_sheets[new_sheet_title]["Path"]
            raise MvError(
                f"Unable to rename '{selected_sheet}' to '{new_sheet_title}' - "
                f"a tracked sheet with this title already exists ({existing_path})"
            )
        logging.info(f"Renaming '{selected_sheet}' to '{new_sheet_title}'")
        shutil.copyfile(
            f"{cogs_dir}/tracked/{selected_sheet}.tsv", f"{cogs_dir}/tracked/{new_sheet_title}.tsv",
        )
        with open(f"{cogs_dir}/renamed.tsv", "a") as f:
            f.write(f"{selected_sheet}\t{new_sheet_title}\t{new_path}\tlocal\n")

    # Get new rows of sheet.tsv to write
    rows = []
    for sheet_title, details in tracked_sheets.items():
        if sheet_title == selected_sheet:
            # Update path and title
            details["Path"] = new_path
            sheet_title = new_sheet_title
        details["Title"] = sheet_title
        rows.append(details)

    # Rewrite sheet.tsv
    with open(f"{cogs_dir}/sheet.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["ID", "Title", "Path", "Description", "Frozen Rows", "Frozen Columns"],
        )
        writer.writeheader()
        writer.writerows(rows)
