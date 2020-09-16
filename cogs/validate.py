import gspread_formatting as gf
import sys

from cogs.exceptions import ValidateError
from cogs.helpers import *


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


def msg():
    return "Apply data validation rules to a sheet"


def clean_rule(sheet_title, loc, condition, value):
    """Validate the arguments for a rule and return the rule as a dict."""
    if not re.compile(r"^[A-Z]+[0-9]+:*[A-Z]*[0-9]*$").match(loc):
        raise ValidateError(f"'{loc}' is not a valid range")

    # Check that condition is valid
    condition = condition.strip().upper()
    if condition not in conditions:
        raise ValidateError(f"'{condition}' is not a valid condition type")

    # Validate the condition + value
    if not value:
        value_list = []
    else:
        value_list = value.strip().split(", ")
    try:
        gf.BooleanCondition(condition, value_list)
    except ValueError:
        if value:
            raise ValidateError(
                f"'{value}' has inappropriate length/content for condition type '{condition}'"
            )
        else:
            raise ValidateError(f"A value or values is required for condition type '{condition}'")

    return {
        "Sheet Title": sheet_title,
        "Range": loc,
        "Condition": condition,
        "Value": value,
    }


def clear_data_validation(spreadsheet, sheet_title):
    """Remove all data validation rules from a sheet."""
    logging.info(f"removing all data validation rules from '{sheet_title}'")
    sheet = spreadsheet.worksheet(sheet_title)
    requests = {
        "requests": [
            {
                "updateCells": {
                    "range": {"sheetId": sheet.id},
                    "fields": "dataValidation",
                }
            }
        ]
    }
    spreadsheet.batch_update(requests)

    # Write empty validation sheet
    with open(".cogs/validation.tsv", "w") as f:
        f.write("Sheet Title\tRange\tCondition\tValue\n")


def get_rules_from_args(args):
    """Retrieve a data validation rule from command line arguments."""
    tracked_sheets = get_tracked_sheets()
    add_rows = []

    # Ensure required args are present
    if not args.sheet:
        raise ValidateError("A sheet title (-s/--sheet) is required")
    if not args.range:
        raise ValidateError("A range (-r/--range) is required")
    if not args.condition:
        raise ValidateError("A condition (-c/--condition) is required")

    sheet_title = args.sheet
    if sheet_title not in tracked_sheets.keys():
        raise ValidateError(f"'{sheet_title}' is not a tracked sheet")
    rule = clean_rule(args.sheet, args.range, args.condition, args.value)
    add_rows.append(rule)
    return add_rows


def get_rules_from_table(path):
    """Retrieve one or more data validation rules from a table."""
    tracked_sheets = get_tracked_sheets()
    add_rows = []

    with open(path, "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            sheet_title = row["Sheet Title"]
            if sheet_title not in tracked_sheets.keys():
                raise ValidateError(f"'{sheet_title}' is not a tracked sheet")
            rule = clean_rule(
                row["Sheet Title"], row["Range"], row["Condition"], row["Value"]
            )
            add_rows.append(rule)
    return add_rows


def validate(args):
    """Apply one or more data validation rules to a sheet OR clear all data validation rules."""
    set_logging(args.verbose)
    validate_cogs_project()

    # If --clear is provided, just clear that sheet and return
    if args.clear:
        config = get_config()
        gc = get_client_from_config(config)
        spreadsheet = gc.open(config["Title"])
        clear_data_validation(spreadsheet, args.clear)
        return

    # Otherwise, apply the data validation rules from either table or args
    if args.apply:
        add_rows = get_rules_from_table(args.apply)
    else:
        add_rows = get_rules_from_args(args)

    # Add to validation.tsv
    add_dv_rules = {}
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


def run(args):
    """Wrapper for validate function."""
    try:
        validate(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
