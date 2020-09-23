import logging
import sys

from cogs.exceptions import ClearError, CogsError
from cogs.helpers import (
    get_data_validation,
    get_sheet_formats,
    get_sheet_notes,
    get_tracked_sheets,
    set_logging,
    update_data_validation,
    update_format,
    update_note,
    validate_cogs_project,
)


def msg():
    return "Clear formatting, notes, or data validation rules from one or more sheets"


def clear_data_validation(sheet_title):
    """Remove all data validation rules from a sheet."""
    sheet_dv_rules = get_data_validation()
    logging.info(f"removing all data validation rules from '{sheet_title}'")
    if sheet_title in sheet_dv_rules:
        del sheet_dv_rules[sheet_title]
    update_data_validation(sheet_dv_rules, [])


def clear_formats(sheet_title):
    """Remove all formats from a sheet."""
    sheet_to_formats = get_sheet_formats()
    logging.info(f"removing all formats from '{sheet_title}'")
    if sheet_title in sheet_to_formats:
        del sheet_to_formats[sheet_title]
    update_format(sheet_to_formats, [])


def clear_notes(sheet_title):
    """Remove all notes from a sheet."""
    sheet_to_notes = get_sheet_notes()
    logging.info(f"removing all notes from '{sheet_title}'")
    if sheet_title in sheet_to_notes:
        del sheet_to_notes[sheet_title]
    update_note(sheet_to_notes, [])


def clear(args):
    """Remove formats, notes, and/or data validation rules from one or more sheets."""
    validate_cogs_project()
    set_logging(args.verbose)
    keyword = args.keyword.lower()
    on_sheets = args.sheets

    # Validate sheets
    tracked_sheets = get_tracked_sheets()

    untracked = []
    for st in on_sheets:
        if st not in tracked_sheets.keys():
            untracked.append(st)
    if untracked:
        raise ClearError(
            f"The following sheet(s) are not part of this project: "
            + ", ".join(untracked)
        )
    if not on_sheets:
        # If no sheet was supplied, clear from all
        on_sheets = tracked_sheets.keys()

    if keyword == "formats":
        for st in on_sheets:
            clear_formats(st)
    elif keyword == "notes":
        for st in on_sheets:
            clear_notes(st)
    elif keyword == "rules":
        for st in on_sheets:
            clear_data_validation(st)
    elif keyword == "all":
        for st in on_sheets:
            clear_formats(st)
            clear_notes(st)
            clear_data_validation(st)
    else:
        raise ClearError("Unknown keyword: " + args.keyword)


def run(args):
    """Wrapper for clear function."""
    try:
        clear(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
