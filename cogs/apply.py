import csv
import logging
import os
import sys

from cogs.exceptions import CogsError
from cogs.helpers import (
    get_sheet_formats,
    get_sheet_notes,
    get_tracked_sheets,
    set_logging,
    validate_cogs_project,
    update_format,
    update_note,
)


def msg():
    return "Apply a standardized problems table to the spreadsheet"


def apply(args):
    """Apply a standardized problems table to the spreadsheet."""
    validate_cogs_project()
    set_logging(args.verbose)
    tracked_sheets = get_tracked_sheets()

    # Get existing formats
    sheet_to_formats = get_sheet_formats()

    # Remove any formats that are "applied" (format ID 0, 1, or 2)
    sheet_to_manual_formats = {}
    for sheet_title, cell_to_formats in sheet_to_formats.items():
        manual_formats = {}
        for cell, fmt in cell_to_formats.items():
            if int(fmt) > 2:
                manual_formats[cell] = fmt
            sheet_to_manual_formats[sheet_title] = manual_formats
    sheet_to_formats = sheet_to_manual_formats

    # Remove any notes that are "applied" (starts with ERROR, WARN, or INFO)
    sheet_to_notes = get_sheet_notes()
    sheet_to_manual_notes = {}
    for sheet_title, cell_to_notes in sheet_to_notes.items():
        manual_notes = {}
        for cell, note in cell_to_notes.items():
            if (
                not note.startswith("ERROR: ")
                and not note.startswith("WARN: ")
                and not note.startswith("INFO: ")
            ):
                manual_notes[cell] = note
        sheet_to_manual_notes[sheet_title] = manual_notes
    sheet_to_notes = sheet_to_manual_notes

    if not args.paths:
        # No table provided - update without adding anything else
        update_note(sheet_to_notes, [])
        update_format(sheet_to_formats, [])
        return

    # Read the problems table to get the formats & notes to add
    for problems_table in args.paths:
        sep = "\t"
        if problems_table.endswith(".csv"):
            sep = ","
        with open(problems_table, "r") as f:
            reader = csv.DictReader(f, delimiter=sep)
            for row in reader:
                table = os.path.splitext(os.path.basename(row["table"]))[0]
                if table not in tracked_sheets:
                    # TODO - error? warning?
                    logging.warning(f"'{table} is not a tracked table")
                    continue

                if table in sheet_to_formats:
                    cell_to_formats = sheet_to_formats[table]
                else:
                    cell_to_formats = {}

                if table in sheet_to_notes:
                    cell_to_notes = sheet_to_notes[table]
                else:
                    cell_to_notes = {}

                cell = row["cell"].upper()

                # Check for current applied formats and/or notes
                current_fmt = -1
                current_note = None
                if cell in cell_to_formats and int(cell_to_formats[cell]) <= 2:
                    current_fmt = cell_to_formats[cell]
                if cell in cell_to_notes:
                    current_note = cell_to_notes[cell]
                    if (
                        not current_note.startswith("ERROR: ")
                        and not current_note.startswith("WARN: ")
                        and not current_note.startswith("INFO: ")
                    ):
                        # Not an applied note
                        current_note = None

                # Set formatting based on level of issue
                level = row["level"].lower().strip()
                if level == "error":
                    cell_to_formats[cell] = 0
                elif level == "warn" or level == "warning":
                    level = "warn"
                    if current_fmt != 0:
                        cell_to_formats[cell] = 1
                elif level == "info":
                    if current_fmt > 1:
                        cell_to_formats[cell] = 2

                instructions = None
                if "instructions" in row:
                    instructions = row["instructions"]
                    if instructions == "":
                        instructions = None

                fix = None
                if "fix" in row:
                    fix = row["fix"]
                    if fix == "":
                        fix = None

                # Add the note
                rule_name = row["rule name"]
                logging.info(f'Adding "{rule_name}" to {cell} as a(n) {level}')

                # Format the note
                note = f"{level.upper()}: {rule_name}"
                if instructions:
                    note += f"\nInstructions: {instructions}"
                if fix:
                    note += f"\nSuggested Fix: \"{fix}\""

                # Add to dict
                if current_note:
                    cell_to_notes[cell] = f"{current_note}\n\n{note}"
                else:
                    cell_to_notes[cell] = note

                sheet_to_formats[table] = cell_to_formats
                sheet_to_notes[table] = cell_to_notes

    # Update formats & notes TSVs
    update_note(sheet_to_notes, [])
    update_format(sheet_to_formats, [])


def run(args):
    """Wrapper for apply function."""
    try:
        apply(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
