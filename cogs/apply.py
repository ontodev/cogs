import sys

from cogs.exceptions import ApplyError
from cogs.helpers import *
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
data_validation_headers = ["table", "cell", "condition", "value"]
problems_headers = [
    "ID",
    "table",
    "cell",
    "level",
    "rule ID",
    "rule name",
    "value",
    "fix",
    "instructions",
]


def msg():
    return "Apply a table to the spreadsheet"


def apply_data_validation(data_valiation_tables):
    """Apply one or more data validation rules to the sheets."""
    tracked_sheets = get_tracked_sheets()
    add_dv_rules = {}
    for data_validation_table in data_valiation_tables:
        add_rows = []
        for row in data_validation_table:
            sheet_title = row["table"]
            if sheet_title not in tracked_sheets.keys():
                raise ApplyError(f"'{sheet_title}' is not a tracked sheet")
            rule = clean_rule(row["table"], row["cell"], row["condition"], row["value"])
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

    update_data_validation(add_dv_rules, [])


def apply_standardized_problems(problems_tables):
    """Apply one or more problems tables (from dict reader) to the sheets as formats and notes."""
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

    # Read the problems table to get the formats & notes to add
    for problems_table in problems_tables:

        for row in problems_table:
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
                note += f'\nSuggested Fix: "{fix}"'

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
            raise ApplyError(
                f"A value or values is required for condition type '{condition}'"
            )

    return {
        "Sheet Title": sheet_title,
        "Range": loc,
        "Condition": condition,
        "Value": value,
    }


def apply(args):
    """Apply a table to the spreadsheet. The type of table to 'apply' is based on the headers:
    standardized problems or data validation."""
    validate_cogs_project()
    set_logging(args.verbose)

    paths = args.paths

    problems_tables = []
    data_validation_tables = []
    for p in paths:
        if p.endswith("csv"):
            sep = ","
        else:
            sep = "\t"
        with open(p, "r") as f:
            reader = csv.DictReader(f, delimiter=sep)
            headers = reader.fieldnames
            rows = []
            for r in reader:
                rows.append(r)
            if headers == problems_headers:
                problems_tables.append(rows)
            elif headers == data_validation_headers:
                data_validation_tables.append(rows)
            else:
                raise ApplyError(f"The headers in table {p} are not valid for apply")

    if problems_tables:
        apply_standardized_problems(problems_tables)

    if data_validation_tables:
        apply_data_validation(data_validation_tables)


def run(args):
    """Wrapper for apply function."""
    try:
        apply(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
