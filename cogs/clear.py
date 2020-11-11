import csv
import logging

from cogs.exceptions import ClearError
from cogs.helpers import (
    get_data_validation,
    get_sheet_formats,
    get_sheet_notes,
    get_tracked_sheets,
    set_logging,
    validate_cogs_project,
)


def clear_data_validation(cogs_dir, sheet_title):
    """Remove all data validation rules from a sheet."""
    sheet_dv_rules = get_data_validation(cogs_dir)
    logging.info(f"removing all data validation rules from '{sheet_title}'")
    if sheet_title in sheet_dv_rules:
        del sheet_dv_rules[sheet_title]

    dv_rows = []
    for sheet_title, dv_rules in sheet_dv_rules.items():
        for row in dv_rules:
            row["Sheet Title"] = sheet_title
            dv_rows.append(row)
    with open(f"{cogs_dir}/validation.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["Sheet Title", "Range", "Condition", "Value"],
        )
        writer.writeheader()
        writer.writerows(dv_rows)


def clear_formats(cogs_dir, sheet_title):
    """Remove all formats from a sheet."""
    sheet_to_formats = get_sheet_formats(cogs_dir)
    logging.info(f"removing all formats from '{sheet_title}'")
    if sheet_title in sheet_to_formats:
        del sheet_to_formats[sheet_title]

    fmt_rows = []
    for sheet_title, formats in sheet_to_formats.items():
        for cell, fmt in formats.items():
            fmt_rows.append({"Sheet Title": sheet_title, "Cell": cell, "Format ID": fmt})
    with open(f"{cogs_dir}/format.tsv", "w") as f:
        writer = csv.DictWriter(
            f, delimiter="\t", lineterminator="\n", fieldnames=["Sheet Title", "Cell", "Format ID"],
        )
        writer.writeheader()
        writer.writerows(fmt_rows)


def clear_notes(cogs_dir, sheet_title):
    """Remove all notes from a sheet."""
    sheet_to_notes = get_sheet_notes(cogs_dir)
    logging.info(f"removing all notes from '{sheet_title}'")
    if sheet_title in sheet_to_notes:
        del sheet_to_notes[sheet_title]

    note_rows = []
    for sheet_title, notes in sheet_to_notes.items():
        for cell, note in notes.items():
            note_rows.append({"Sheet Title": sheet_title, "Cell": cell, "Note": note})
    with open(f"{cogs_dir}/note.tsv", "w") as f:
        writer = csv.DictWriter(
            f, delimiter="\t", lineterminator="\n", fieldnames=["Sheet Title", "Cell", "Note"],
        )
        writer.writeheader()
        writer.writerows(note_rows)


def clear(keyword, on_sheets=None, verbose=False):
    """Remove formats, notes, and/or data validation rules from one or more sheets."""
    cogs_dir = validate_cogs_project()
    set_logging(verbose)

    # Validate sheets
    tracked_sheets = get_tracked_sheets(cogs_dir)

    if not on_sheets:
        # If no sheet was supplied, clear from all
        on_sheets = tracked_sheets.keys()

    untracked = []
    for st in on_sheets:
        if st not in tracked_sheets.keys():
            untracked.append(st)
    if untracked:
        raise ClearError(
            f"The following sheet(s) are not part of this project: " + ", ".join(untracked)
        )

    if keyword == "formats":
        for st in on_sheets:
            clear_formats(cogs_dir, st)
    elif keyword == "notes":
        for st in on_sheets:
            clear_notes(cogs_dir, st)
    elif keyword == "validation":
        for st in on_sheets:
            clear_data_validation(cogs_dir, st)
    elif keyword == "all":
        for st in on_sheets:
            clear_formats(cogs_dir, st)
            clear_notes(cogs_dir, st)
            clear_data_validation(cogs_dir, st)
    else:
        raise ClearError("Unknown keyword: " + keyword)
