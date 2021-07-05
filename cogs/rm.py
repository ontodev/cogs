import csv
import os

from cogs.exceptions import RmError
from cogs.helpers import (
    get_cached_path,
    get_tracked_sheets,
    set_logging,
    validate_cogs_project,
    get_sheet_formats,
    update_format,
    get_sheet_notes,
    update_note,
)


def rm(paths, keep=False, verbose=False):
    """Remove a table (TSV or CSV) from the COGS project.
    This updates sheet.tsv and deletes the corresponding cached file."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()

    # Make sure the sheets exist
    sheets = get_tracked_sheets(cogs_dir)
    path_to_sheet = {
        os.path.abspath(details["Path"]): sheet_title for sheet_title, details in sheets.items()
    }

    # Check for either untracked or ignored sheets in provided paths
    ignore = [x for x, y in sheets.items() if y.get("Ignore")]
    untracked = []
    ignored = []
    for p in paths:
        abspath = os.path.abspath(p)
        if abspath not in path_to_sheet:
            untracked.append(p)
        elif path_to_sheet[abspath] in ignore:
            ignored.append(p)
    if untracked:
        raise RmError(f"unable to remove untracked file(s): {', '.join(untracked)}.")
    if ignored:
        raise RmError(f"unable to remove ignored file(s): {', '.join(ignored)}")

    sheets_to_remove = {title: sheet for title, sheet in sheets.items() if sheet["Path"] in paths}

    # Make sure we are not deleting the last sheet as Google spreadsheet would refuse to do so
    if len(sheets) - len(sheets_to_remove) == 0:
        raise RmError(
            f"unable to remove {len(sheets_to_remove)} tracked sheet(s) - "
            "the spreadsheet must have at least one sheet."
        )

    # Maybe remove local copies
    if not keep:
        for p in paths:
            if os.path.exists(p):
                os.remove(p)

    # Remove the cached copies
    for sheet_title in sheets_to_remove.keys():
        cached_path = get_cached_path(cogs_dir, sheet_title)
        if os.path.exists(cached_path):
            os.remove(cached_path)

    # Update sheet.tsv
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
        for title, sheet in sheets.items():
            if title not in sheets_to_remove.keys():
                sheet["Title"] = title
                writer.writerow(sheet)

    # Update formats and notes
    sheet_formats = get_sheet_formats(cogs_dir)
    update_format(cogs_dir, sheet_formats, sheets_to_remove.keys())

    sheet_notes = get_sheet_notes(cogs_dir)
    update_note(cogs_dir, sheet_notes, sheets_to_remove.keys())
