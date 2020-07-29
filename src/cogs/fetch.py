import csv
import logging
import os
import sys

from cogs.exceptions import CogsError, FetchError
from cogs.helpers import (
    get_config,
    get_client,
    get_renamed_sheets,
    get_tracked_sheets,
    maybe_update_fields,
    set_logging,
    validate_cogs_project,
)


def get_remote_sheets(sheets):
    """Retrieve a map of sheet title -> sheet ID from the spreadsheet."""
    # Validate sheet titles before downloading anything
    remote_sheets = {}
    for sheet in sheets:
        if sheet.title in ["user", "config", "sheet", "field", "renamed"]:
            raise FetchError(
                f"cannot export remote sheet with the reserved name '{sheet.title}'"
            )
        remote_sheets[sheet.title] = sheet.id
    return remote_sheets


def fetch(args):
    """Fetch all sheets from project spreadsheet to .cogs/ directory."""
    set_logging(args.verbose)
    validate_cogs_project()

    config = get_config()
    client = get_client(config["Credentials"])
    title = config["Title"]
    spreadsheet = client.open(title)

    # Get existing fields (headers) to see if we need to add/remove fields
    headers = []

    # Get the remote sheets from spreadsheet
    sheets = spreadsheet.worksheets()
    remote_sheets = get_remote_sheets(sheets)
    tracked_sheets = get_tracked_sheets()
    id_to_title = {
        int(details["ID"]): sheet_title for sheet_title, details in tracked_sheets.items()
    }

    # Get details about renamed sheets
    renamed_local = get_renamed_sheets()
    new_local_titles = [details["new"] for details in renamed_local.values()]
    renamed_remote = {}

    # Export the sheets as TSV to .cogs/ (while checking the fieldnames)
    for sheet in sheets:
        # Download the sheet as the renamed sheet if necessary
        if sheet.title in renamed_local:
            st = renamed_local[sheet.title]["new"]
            logging.info(
                f"Downloading remote sheet '{sheet.title}' as {st} (renamed locally)"
            )
        else:
            st = sheet.title
            if sheet.id in id_to_title:
                local_title = id_to_title[sheet.id]
                if local_title != sheet.title:
                    # The sheet title has been changed remotely
                    # This will be updated in tracking but the local sheet will remain
                    old_path = tracked_sheets[local_title]["Path"]
                    logging.warning(
                        f"Local sheet '{local_title}' has been renamed to '{st}' remotely:"
                        f"\n  - '{local_title}' is removed from tracking and replaced with '{st}'"
                        f"\n  - {old_path} will not be updated when running `cogs pull` "
                        f"\n  - changes to {old_path} will not be pushed to the remote spreadsheet"
                    )
                    renamed_remote[local_title] = {"new": st, "path": st + ".tsv"}
            logging.info(f"Downloading remote sheet '{st}'")
        with open(f".cogs/{st}.tsv", "w") as f:
            lines = sheet.get_all_values()
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerows(lines)
            if lines:
                headers.extend(lines[0])

    # Maybe update fields if they have changed
    maybe_update_fields(headers)

    # Update local sheets with new IDs
    all_sheets = []
    for sheet_title, details in tracked_sheets.items():
        if sheet_title in remote_sheets:
            sid = remote_sheets[sheet_title]
            details["ID"] = sid
        details["Title"] = sheet_title
        all_sheets.append(details)

    # Get all cached sheet titles that are not COGS defaults
    cached_sheet_titles = []
    for f in os.listdir(".cogs"):
        if f not in ["user.tsv", "sheet.tsv", "field.tsv", "config.tsv", "renamed.tsv"]:
            cached_sheet_titles.append(f.split(".")[0])

    # If a cached sheet title is not in sheet.tsv & not in remote sheets - remove it
    remote_titles = [x.title for x in sheets]
    for sheet_title in cached_sheet_titles:
        if sheet_title not in remote_titles and sheet_title not in new_local_titles:
            # This sheet has a cached copy but does not exist in the remote version
            # It has either been removed from remote or was newly added to cache
            if (
                sheet_title in tracked_sheets
                and tracked_sheets[sheet_title]["ID"].strip != ""
            ) or (sheet_title not in tracked_sheets):
                # The sheet is in tracked sheets and has an ID (not newly added)
                # or the sheet is not in tracked sheets
                logging.info(f"Removing '{sheet_title}'")
                os.remove(f".cogs/{sheet_title}.tsv")

    # Get just the remote sheets that are not in local sheets
    new_sheets = {
        sheet_title: sid
        for sheet_title, sid in remote_sheets.items()
        if sheet_title not in tracked_sheets
    }
    for sheet_title, sid in new_sheets.items():
        if sheet_title not in renamed_local:
            logging.info(f"new sheet '{sheet_title}' added to project")
            details = {
                "ID": sid,
                "Title": sheet_title,
                "Path": f"{sheet_title}.tsv",
                "Description": "",
            }
            all_sheets.append(details)

    # Then update sheet.tsv
    with open(".cogs/sheet.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["ID", "Title", "Path", "Description"],
        )
        writer.writeheader()
        writer.writerows(all_sheets)


def run(args):
    """Wrapper for fetch function."""
    try:
        fetch(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
