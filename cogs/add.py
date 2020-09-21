import ntpath
import sys

from cogs.helpers import *
from cogs.exceptions import CogsError, AddError


def msg():
    return "Add a table (TSV or CSV) to the project"


def maybe_update_fields(headers):
    """Check fieldnames in headers and add to field.tsv if they do not exist."""
    fields = get_fields()
    update_fields = False
    for h in headers:
        field = re.sub(r"[^A-Za-z0-9]+", "_", h.lower()).strip("_")
        if field not in fields:
            update_fields = True
            fields[field] = {"Label": h, "Datatype": "cogs:text", "Description": ""}

    # Update field.tsv if we need to
    if update_fields:
        with open(".cogs/field.tsv", "w") as f:
            writer = csv.DictWriter(
                f,
                delimiter="\t",
                lineterminator="\n",
                fieldnames=["Field", "Label", "Datatype", "Description"],
            )
            writer.writeheader()
            for field, items in fields.items():
                items["Field"] = field
                writer.writerow(items)


def add(args):
    """Add a table (TSV or CSV) to the COGS project. This updates sheet.tsv and field.tsv."""
    set_logging(args.verbose)
    validate_cogs_project()

    # Open the provided file and make sure we can parse it as TSV or CSV
    path = args.path
    if path.endswith(".csv"):
        delimiter = ","
        fmt = "CSV"
    else:
        delimiter = "\t"
        fmt = "TSV"
    with open(path, "r") as f:
        try:
            reader = csv.DictReader(f, delimiter=delimiter)
        except csv.Error as e:
            raise AddError(f"unable to read {path} as {fmt}\nCAUSE:{str(e)}")
        headers = reader.fieldnames

    if args.title:
        # Get the title from args
        title = args.title
    else:
        # Create the sheet title from file basename
        title = ntpath.basename(path).split(".")[0]
    if title in reserved_names:
        raise AddError(f"sheet cannot use reserved name '{title}'")

    # Make sure we aren't duplicating a table
    local_sheets = get_tracked_sheets()
    if title in local_sheets:
        raise AddError(f"'{title}' sheet already exists in this project")

    # Make sure we aren't duplicating a path
    local_paths = {x["Path"]: t for t, x in local_sheets.items()}
    if path in local_paths.keys():
        other_title = local_paths[path]
        raise AddError(f"Local table {path} already exists as '{other_title}'")

    # Maybe get a description
    description = ""
    if args.description:
        description = args.description

    if headers:
        maybe_update_fields(headers)

    # Finally, add this TSV to sheet.tsv
    with open(".cogs/sheet.tsv", "a") as f:
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
            ],
        )
        # ID gets filled in when we add it to the Sheet
        writer.writerow(
            {
                "ID": "",
                "Title": title,
                "Path": path,
                "Description": description,
                "Frozen Rows": args.freeze_row,
                "Frozen Columns": args.freeze_column,
            }
        )

    logging.info(f"{title} successfully added to project")


def run(args):
    """Wrapper for add function."""
    try:
        add(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
