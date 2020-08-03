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
    update_note
)


def apply(args):
    """Apply a standardized ROBOT problems table to the spreadsheet."""
    validate_cogs_project()
    set_logging(args.verbose)
    tracked_sheets = get_tracked_sheets()

    # Get existing formats
    sheet_to_formats = get_sheet_formats()
    sheet_to_notes = {}

    # Read the problems table to get the formats & notes to add
    sep = "\t"
    if args.problems_table.endswith(".csv"):
        sep = ","
    with open(args.problems_table, "r") as f:
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
            level = row["level"].lower().strip()
            if level == "error":
                cell_to_formats[cell] = 0
            elif level == "warn" or level == "warning":
                cell_to_formats[cell] = 1
            elif level == "info":
                cell_to_formats[cell] = 2

            rule_name = row["rule name"]
            logging.info(f"Adding \"{rule_name}\" to {cell} as a(n) {level}")
            cell_to_notes[cell] = rule_name

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
