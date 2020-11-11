import csv
import logging
import os
import re

from cogs.exceptions import ApplyError
from cogs.helpers import (
    get_tracked_sheets,
    update_data_validation,
    get_sheet_formats,
    get_sheet_notes,
    update_note,
    update_format,
    validate_cogs_project,
    set_logging,
)
from gspread_formatting import BooleanCondition


# data validation conditions
conditions = [
    "NUMBER_GREATER" "NUMBER_GREATER_THAN_EQ",
    "NUMBER_LESS",
    "NUMBER_LESS_THAN_EQ",
    "NUMBER_EQ",
    "NUMBER_NOT_EQ",
    "NUMBER_BETWEEN",
    "NUMBER_NOT_BETWEEN",
    "TEXT_CONTAINS",
    "TEXT_NOT_CONTAINS",
    "TEXT_STARTS_WITH",
    "TEXT_ENDS_WITH",
    "TEXT_EQ",
    "TEXT_IS_EMAIL",
    "TEXT_IS_URL",
    "DATE_EQ",
    "DATE_BEFORE",
    "DATE_AFTER",
    "DATE_ON_OR_BEFORE",
    "DATE_ON_OR_AFTER",
    "DATE_BETWEEN",
    "DATE_NOT_BETWEEN",
    "DATE_IS_VALID",
    "ONE_OF_RANGE",
    "ONE_OF_LIST",
    "BLANK",
    "NOT_BLANK",
    "CUSTOM_FORMULA",
    "BOOLEAN",
]

# expected headers for different tables
data_validation_headers = ["table", "range", "condition", "value"]
message_headers = ["table", "cell", "level", "rule id", "rule", "message", "suggestion"]


def apply_data_validation(cogs_dir, data_valiation_tables):
    """Apply one or more data validation rules to the sheets."""
    tracked_sheets = get_tracked_sheets(cogs_dir)
    add_dv_rules = {}
    for data_validation_table in data_valiation_tables:
        add_rows = []
        for row in data_validation_table:
            sheet_title = row["table"]
            if sheet_title not in tracked_sheets.keys():
                raise ApplyError(f"'{sheet_title}' is not a tracked sheet")
            rule = clean_rule(row["table"], row["range"], row["condition"], row["value"])
            add_rows.append(rule)

        for row in add_rows:
            sheet_title = row["Sheet Title"]
            del row["Sheet Title"]
            if sheet_title in add_dv_rules:
                dv_rules = add_dv_rules[sheet_title]
            else:
                dv_rules = []
            dv_rules.append(row)
            add_dv_rules[sheet_title] = dv_rules

    update_data_validation(cogs_dir, add_dv_rules, [])


def apply_messages(cogs_dir, message_tables):
    """Apply one or more message tables (from dict reader) to the sheets as formats and notes."""
    tracked_sheets = get_tracked_sheets(cogs_dir)
    # Get existing formats
    sheet_to_formats = get_sheet_formats(cogs_dir)

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
    sheet_to_notes = get_sheet_notes(cogs_dir)
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

    # Read the message table to get the formats & notes to add
    for message_table in message_tables:

        for row in message_table:
            table = os.path.splitext(os.path.basename(row["table"]))[0]
            if table not in tracked_sheets:
                # TODO - error? warning?
                logging.warning(f"'{table}' is not a tracked sheet")
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
                    not current_note.startswith("ERROR")
                    and not current_note.startswith("WARN")
                    and not current_note.startswith("INFO")
                ):
                    # Not an applied note
                    current_note = None

            # Set formatting based on level of issue
            if "level" in row:
                level = row["level"].lower().strip()
            else:
                level = "error"
            if level == "error":
                cell_to_formats[cell] = 0
            elif level == "warn" or level == "warning":
                level = "warn"
                if current_fmt != 0:
                    cell_to_formats[cell] = 1
            elif level == "info":
                if current_fmt < 1:
                    cell_to_formats[cell] = 2

            message = None
            if "message" in row:
                message = row["message"]
                if message == "":
                    message = None

            suggest = None
            if "suggestion" in row:
                suggest = row["suggestion"]
                if suggest == "":
                    suggest = None

            rule_id = None
            if "rule id" in row:
                rule_id = row["rule id"]

            # Add the note
            rule_name = None
            if "rule" in row:
                rule_name = row["rule"]
                logging.info(f'Adding "{rule_name}" to {cell} as a(n) {level}')
            else:
                logging.info(f"Adding message to {cell} as a(n) {level}")

            # Format the note
            if rule_name:
                note = f"{level.upper()}: {rule_name}"
            else:
                note = level.upper()
            if message:
                note += f"\n{message}"
            if suggest:
                note += f'\nSuggested Fix: "{suggest}"'
            if rule_id:
                note += f"\nFor more details, see {rule_id}"

            # Add to dict
            if current_note:
                cell_to_notes[cell] = f"{current_note}\n\n{note}"
            else:
                cell_to_notes[cell] = note

            sheet_to_formats[table] = cell_to_formats
            sheet_to_notes[table] = cell_to_notes

    # Update formats & notes TSVs
    update_note(cogs_dir, sheet_to_notes, [])
    update_format(cogs_dir, sheet_to_formats, [])


def clean_rule(sheet_title, loc, condition, value):
    """Validate the arguments for a rule and return the rule as a dict."""
    if not re.compile(r"^[A-Z]+[0-9]+:*[A-Z]*[0-9]*$").match(loc):
        raise ApplyError(f"'{loc}' is not a valid range")

    # Check that condition is valid
    condition = condition.strip().upper()
    if condition not in conditions:
        raise ApplyError(f"'{condition}' is not a valid condition type")

    # Validate the condition + value
    if not value:
        value_list = []
    else:
        value_list = value.strip().split(", ")
    try:
        BooleanCondition(condition, value_list)
    except ValueError:
        if value:
            raise ApplyError(
                f"'{value}' has inappropriate length/content for condition type '{condition}'"
            )
        else:
            raise ApplyError(f"A value or values is required for condition type '{condition}'")

    return {
        "Sheet Title": sheet_title,
        "Range": loc,
        "Condition": condition,
        "Value": value,
    }


def apply(paths, verbose=False):
    """Apply a table to the spreadsheet. The type of table to 'apply' is based on the headers:
    standardized messages or data validation."""
    cogs_dir = validate_cogs_project()
    set_logging(verbose)

    message_tables = []
    data_validation_tables = []
    for p in paths:
        if p.endswith("csv"):
            sep = ","
        else:
            sep = "\t"
        with open(p, "r") as f:
            # Get headers and rows
            reader = csv.DictReader(f, delimiter=sep)
            headers = [x.lower() for x in reader.fieldnames]
            rows = []
            for r in reader:
                rows.append({k.lower(): v for k, v in r.items()})

            # Determine type of table
            if headers == data_validation_headers:
                data_validation_tables.append(rows)
            elif "table" in headers and "cell" in headers:
                for h in headers:
                    if h not in message_headers:
                        raise ApplyError(f"The headers in table {p} are not valid for apply")
                message_tables.append(rows)
            else:
                raise ApplyError(f"The headers in table {p} are not valid for apply")

    if message_tables:
        apply_messages(cogs_dir, message_tables)

    if data_validation_tables:
        apply_data_validation(cogs_dir, data_validation_tables)
