import shutil

from cogs.exceptions import MvError
from cogs.helpers import *


def mv(path, new_path, new_title=None, force=False, verbose=False):
    """Move a local sheet to a new local path. If the file basename changes, the sheet title will
    also change."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()

    if not os.path.exists(path):
        raise MvError(f"{path} does not exist")

    if os.path.isdir(new_path):
        # Move the old file into the given directory
        new_path = os.path.join(new_path, os.path.basename(path))

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

    # Make sure the sheet we are moving is not ignored
    ignore = [x for x, y in tracked_sheets.items() if y.get("Ignore")]
    if path_to_sheet[cur_path] in ignore:
        raise MvError(f"{path} is an ignored sheet and cannot be moved")

    # Move the local copy if it exists
    # If it doesn't exist, the user has already moved to the new path
    if os.path.exists(path):
        os.rename(path, new_path)

    # See if the basename (sheet title) changed
    # If so, we need to rename the cached copy
    selected_sheet = path_to_sheet[cur_path]
    if new_title:
        new_cached_path = get_cached_path(cogs_dir, new_title)
        if os.path.exists(new_cached_path):
            # A cached sheet with this name already exists
            existing_path = tracked_sheets[new_title]["Path"]
            raise MvError(
                f"Unable to rename '{selected_sheet}' to '{new_title}' - "
                f"a tracked sheet with this title already exists ({existing_path})"
            )

        logging.info(f"Renaming '{selected_sheet}' to '{new_title}'")

        # Check if cached path exists - may not if it has not been pushed or pulled yet
        old_cached_path = get_cached_path(cogs_dir, selected_sheet)
        if os.path.exists(old_cached_path):
            shutil.copyfile(old_cached_path, new_cached_path)

        # Add to renamed.tsv
        with open(f"{cogs_dir}/renamed.tsv", "a") as f:
            f.write(f"{selected_sheet}\t{new_title}\t{new_path}\tlocal\n")

        # Maybe update format.tsv
        sheet_formats = get_sheet_formats(cogs_dir)
        this_formats = sheet_formats.get(selected_sheet)
        if this_formats:
            del sheet_formats[selected_sheet]
            sheet_formats[new_title] = this_formats
            update_format(cogs_dir, sheet_formats, [], overwrite=True)

        # Maybe update notes.tsv
        sheet_notes = get_sheet_notes(cogs_dir)
        this_notes = sheet_notes.get(selected_sheet)
        if this_notes:
            del sheet_notes[selected_sheet]
            sheet_notes[new_title] = this_notes
            update_note(cogs_dir, sheet_notes, [])

        # Maybe update validation.tsv
        data_validation = get_data_validation(cogs_dir)
        this_dv = data_validation.get(selected_sheet)
        if this_dv:
            del data_validation[selected_sheet]
            data_validation[new_title] = this_dv
            update_data_validation(cogs_dir, data_validation, [])

    # Get new rows of sheet.tsv to write
    rows = []
    for sheet_title, details in tracked_sheets.items():
        if sheet_title == selected_sheet:
            # Update path and title
            details["Path"] = new_path
            sheet_title = new_title or sheet_title
        details["Title"] = sheet_title
        rows.append(details)

    # Rewrite sheet.tsv
    with open(f"{cogs_dir}/sheet.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=[
                "ID",
                "Title",
                "Path",
                "Description",
                "Frozen Rows",
                "Frozen Columns",
                "Ignore",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
