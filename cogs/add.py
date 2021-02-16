import csv
import logging
import ntpath

from cogs.helpers import get_tracked_sheets, set_logging, validate_cogs_project
from cogs.exceptions import AddError


def add(path, title=None, description=None, freeze_row=0, freeze_column=0, verbose=False):
    """Add a table (TSV or CSV) to the COGS project. This updates sheet.tsv."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()

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

    # Finally, add this TSV to sheet.tsv
    with open(f"{cogs_dir}/sheet.tsv", "a") as f:
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
                "Ignore",
            ],
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
                "Ignore": False,
            }
        )

    logging.info(f"{title} successfully added to project")
