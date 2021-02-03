import csv

from cogs.exceptions import RmError
from cogs.helpers import (
    get_tracked_sheets,
    set_logging,
    validate_cogs_project,
    get_sheet_formats,
    update_format,
    get_sheet_notes,
    update_note,
)


def rm(paths, verbose=False):
    """Remove a table (TSV or CSV) from the COGS project. 
    This updates sheet.tsv and field.tsv and delete the according cached file."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()

    # Make sure the sheets exist
    sheets = get_tracked_sheets(cogs_dir)

    tracked_paths = [sheet["Path"] for sheet in sheets.values()]
    if len(set(tracked_paths) - set(tracked_paths)) > 0:
        raise RmError(
            f"unable to remove untracked file(s): {' '.join(set(paths)-set(tracked_paths))}."
        )

    sheets_to_remove = {title: sheet for title, sheet in sheets.items() if sheet["Path"] in paths}

    # Make sure we are not deleting the last sheet as Google spreadsheet would refuse to do so
    if len(sheets) - len(sheets_to_remove) == 0:
        raise RmError(
            f"unable to remove {len(sheets_to_remove)} tracked sheet(s) - "
            "the spreadsheet must have at least one sheet."
        )

    # Make sure the titles are valid
    for sheet_title in sheets_to_remove.keys():
        if "." in sheet_title or "/" in sheet_title:
            # We should probably use a proper way to make sure the file name is in .cogs
            raise RmError("Invalid title for sheet, cannot contain . or /")

    # Update sheet.tsv
    with open(f"{cogs_dir}/sheet.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["ID", "Title", "Path", "Description", "Frozen Rows", "Frozen Columns"],
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
