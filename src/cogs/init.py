import csv
import gspread
import os
import pkg_resources
import sys

from cogs.exceptions import CogsError, InitError
from cogs.helpers import get_client, is_email, is_valid_role
from cogs.cli import get_version


default_fields = [
    {
        "Field": "sheet",
        "Label": "Sheet",
        "Datatype": "cogs:sql_id",
        "Description": "The identifier for this sheet",
    },
    {
        "Field": "label",
        "Label": "Label",
        "Datatype": "cogs:label",
        "Description": "The label for this row",
    },
    {
        "Field": "file_path",
        "Label": "File Path",
        "Datatype": "cogs:file_path",
        "Description": "The relative path of the TSV file for this sheet",
    },
    {
        "Field": "description",
        "Label": "Description",
        "Datatype": "cogs:text",
        "Description": "A description of this row",
    },
    {
        "Field": "field",
        "Label": "Field",
        "Datatype": "cogs:sql_id",
        "Description": "The identifier for this field",
    },
    {
        "Field": "datatype",
        "Label": "Datatype",
        "Datatype": "cogs:curie",
        "Description": "The datatype for this row",
    },
]


def get_users(args):
    """Return a dict of user emails to their roles."""
    users = {}

    # Single user specified
    if args.user:
        # Validate the email
        if not is_email(args.user):
            raise InitError(f"ERROR: {args.user} is not a valid email")

        # Validate the role
        if not is_valid_role(args.role):
            raise InitError(f"ERROR: '{args.role}' is not a valid role")
        users[args.user] = args.role

    # Multiple users specified
    if args.users:
        if not os.path.exists(args.users):
            raise InitError(f"ERROR: users file '{args.users}' does not exist")
        with open(args.users, "r") as f:
            reader = csv.reader(f, delimiter="\t")
            i = 1
            for row in reader:
                email = row[0]
                role = row[1].strip().lower()
                if not is_email(email):
                    if i == 1:
                        # Skip the first line if it does not have an email in the first column
                        # Allowing for users to have their own headers, or not
                        continue
                    else:
                        # Any line past the first should always have an email in the first column
                        raise InitError(
                            f"ERROR: {email} is not a valid email address ({args.users}, line {i})"
                        )

                # Validate the role
                if not is_valid_role(role):
                    raise InitError(
                        f"ERROR: '{role}' is not a valid role ({args.users}, line {i})"
                    )

                users[email] = role
                i += 1
    return users

def write_data(args, sheet):
    """Create COGS data files: config.tsv, sheet.tsv, and field.tsv."""
    # Store COGS configuration
    with open(".cogs/config.tsv", "w") as f:
        writer = csv.DictWriter(
            f, delimiter="\t", lineterminator="\n", fieldnames=["Key", "Value"]
        )
        v = get_version()
        writer.writerow({"Key": "COGS", "Value": "https://github.com/ontodev/cogs"})
        writer.writerow({"Key": "COGS Version", "Value": v})
        writer.writerow({"Key": "Credentials", "Value": args.credentials})
        writer.writerow({"Key": "Title", "Value": args.title})
        writer.writerow({"Key": "Spreadsheet ID", "Value": sheet.id})

    # sheet.tsv contains sheet (table/tab) details from the spreadsheet
    with open(".cogs/sheet.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["ID", "Title", "Path", "Description"],
        )
        writer.writeheader()

    # field.tsv contains the field headers used in the sheets
    with open(".cogs/field.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["Field", "Label", "Datatype", "Description"],
        )
        writer.writeheader()
        writer.writerows(default_fields)


def init(args):
    """Init a new .cogs configuration directory in the current working directory. If one already
        exists, display an error message."""
    cwd = os.getcwd()
    if os.path.exists(".cogs"):
        print(f"ERROR: COGS project already exists in {cwd}/.cogs/")
        sys.exit(1)

    print(f"Initializing COGS project '{args.title}' in {cwd}/.cogs/")
    os.mkdir(".cogs")

    # Process supplied users
    users = get_users(args)

    # Create a Client to access API
    gc = get_client(args.credentials)

    # Create the new Sheet
    try:
        spreadsheet = gc.create(args.title)
    except gspread.exceptions.APIError as e:
        raise InitError(
            f"ERROR: Unable to create new spreadsheet '{args.title}'\n"
            f"CAUSE: {e.response.text}"
        )

    # Share with each user
    for email, role in users.items():
        try:
            spreadsheet.share(email, perm_type="user", role=role)
        except gspread.exceptions.APIError as e:
            print(f"ERROR: Unable to share '{args.title}' with {email} as {role}")
            print(e.response.text)

    # Write data to COGS directory
    write_data(args, spreadsheet)


def run(args):
    """Wrapper for init function."""
    try:
        init(args)
    except CogsError as e:
        print(str(e))
        if os.path.exists(".cogs"):
            os.rmdir(".cogs")
        sys.exit(1)
