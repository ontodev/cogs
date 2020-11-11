import csv
import logging
import ntpath
import re

from cogs.helpers import get_fields, get_tracked_sheets, set_logging, validate_cogs_project
from cogs.exceptions import AddError


def maybe_update_fields(cogs_dir, headers):
    """Check fieldnames in headers and add to field.tsv if they do not exist."""
    fields = get_fields(cogs_dir)
    update_fields = False
    for h in headers:
        field = re.sub(r"[^A-Za-z0-9]+", "_", h.lower()).strip("_")
        if field not in fields:
            update_fields = True
            fields[field] = {"Label": h, "Datatype": "cogs:text", "Description": ""}

    # Update field.tsv if we need to
    if update_fields:
        with open(f"{cogs_dir}/field.tsv", "w") as f:
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


def add(path, title=None, description=None, freeze_row=0, freeze_column=0, verbose=False):
    """Add a table (TSV or CSV) to the COGS project. This updates sheet.tsv and field.tsv."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()

    # Open the provided file and make sure we can parse it as TSV or CSV
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

    if not title:
        # Create the sheet title from file basename
        title = ntpath.basename(path).split(".")[0]

    # Make sure we aren't duplicating a table
    local_sheets = get_tracked_sheets(cogs_dir)
    if title in local_sheets:
        raise AddError(f"'{title}' sheet already exists in this project")

    # Make sure we aren't duplicating a path
    local_paths = {x["Path"]: t for t, x in local_sheets.items()}
    if path in local_paths.keys():
        other_title = local_paths[path]
        raise AddError(f"Local table {path} already exists as '{other_title}'")

    # Maybe get a description
    if not description:
        description = ""

    if headers:
        maybe_update_fields(cogs_dir, headers)

    # Finally, add this TSV to sheet.tsv
    with open(f"{cogs_dir}/sheet.tsv", "a") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["ID", "Title", "Path", "Description", "Frozen Rows", "Frozen Columns"],
        )
        # ID gets filled in when we add it to the Sheet
        writer.writerow(
            {
                "ID": "",
                "Title": title,
                "Path": path,
                "Description": description,
                "Frozen Rows": freeze_row,
                "Frozen Columns": freeze_column,
            }
        )

    logging.info(f"{title} successfully added to project")
