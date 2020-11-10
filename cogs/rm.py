import csv
import os

from cogs.exceptions import RmError
from cogs.helpers import (
    get_fields,
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

    # Get the headers from all files and remove only the ones that are unique to the tracked file(s)
    fields_all = set()
    fields_candidates_for_removal = set()

    for title, sheet in sheets.items():
        if (
            not os.path.exists(f"{cogs_dir}/tracked/{title}.tsv")
            or os.stat(f"{cogs_dir}/tracked/{title}.tsv").st_size == 0
        ):
            continue
        path = f"{cogs_dir}/tracked/{title}.tsv"
        with open(path, "r") as sheet_file:
            try:
                reader = csv.DictReader(sheet_file, delimiter="\t")
            except csv.Error as e:
                raise RmError(f"unable to read {path} as a TSV\nCAUSE:{str(e)}")

            if title in sheets_to_remove.keys():
                fields_candidates_for_removal = fields_candidates_for_removal | set(
                    reader.fieldnames
                )
            else:
                fields_all = fields_all | set(reader.fieldnames)

    fields_to_remove = fields_candidates_for_removal - fields_all

    original_fields = get_fields(cogs_dir)

    with open(f"{cogs_dir}/field.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["Field", "Label", "Datatype", "Description"],
        )
        writer.writeheader()
        for field, items in original_fields.items():
            if items["Label"] not in fields_to_remove:
                items["Field"] = field
                writer.writerow(items)

    # Update formats and notes
    sheet_formats = get_sheet_formats(cogs_dir)
    update_format(cogs_dir, sheet_formats, sheets_to_remove.keys())

    sheet_notes = get_sheet_notes(cogs_dir)
    update_note(cogs_dir, sheet_notes, sheets_to_remove.keys())
