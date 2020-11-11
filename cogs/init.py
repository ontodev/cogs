import warnings

from cogs.exceptions import InitError
from cogs.helpers import *


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

# 0 = error, 1 = warn, 2 = info
default_formats = {
    "0": {
        "backgroundColor": {"blue": 0.7019608, "green": 0.7019608, "red": 1},
        "backgroundColorStyle": {"rgbColor": {"blue": 0.7019608, "green": 0.7019608, "red": 1}},
        "borders": {
            "bottom": {"color": {}, "colorStyle": {"rgbColor": {}}, "style": "SOLID", "width": 1,},
            "left": {"color": {}, "colorStyle": {"rgbColor": {}}, "style": "SOLID", "width": 1,},
            "right": {"color": {}, "colorStyle": {"rgbColor": {}}, "style": "SOLID", "width": 1,},
            "top": {"color": {}, "colorStyle": {"rgbColor": {}}, "style": "SOLID", "width": 1,},
        },
    },
    "1": {
        "backgroundColor": {"blue": 0.5921569, "green": 1, "red": 1},
        "backgroundColorStyle": {"rgbColor": {"blue": 0.5921569, "green": 1, "red": 1}},
        "borders": {
            "bottom": {"color": {}, "colorStyle": {"rgbColor": {}}, "style": "SOLID", "width": 1,},
            "left": {"color": {}, "colorStyle": {"rgbColor": {}}, "style": "SOLID", "width": 1,},
            "right": {"color": {}, "colorStyle": {"rgbColor": {}}, "style": "SOLID", "width": 1,},
            "top": {"color": {}, "colorStyle": {"rgbColor": {}}, "style": "SOLID", "width": 1,},
        },
    },
    "2": {
        "backgroundColor": {"blue": 1, "green": 0.87058824, "red": 0.7254902},
        "backgroundColorStyle": {"rgbColor": {"blue": 1, "green": 0.87058824, "red": 0.7254902}},
        "borders": {
            "bottom": {"color": {}, "colorStyle": {"rgbColor": {}}, "style": "SOLID", "width": 1,},
            "left": {"color": {}, "colorStyle": {"rgbColor": {}}, "style": "SOLID", "width": 1,},
            "right": {"color": {}, "colorStyle": {"rgbColor": {}}, "style": "SOLID", "width": 1,},
            "top": {"color": {}, "colorStyle": {"rgbColor": {}}, "style": "SOLID", "width": 1,},
        },
    },
}


def get_users(user=None, users_file=None, role="writer"):
    """Return a dict of user emails to their roles."""
    users = {}

    # Single user specified
    if user:
        # Validate the email
        if not is_email(user):
            raise InitError(f"{user} is not a valid email")

        # Validate the role
        if not is_valid_role(role):
            raise InitError(f"'{role}' is not a valid role")
        users[user] = role

    # Multiple users specified
    elif users_file:
        if not os.path.exists(users_file):
            raise InitError(f"users file '{users_file}' does not exist")
        with open(users_file, "r") as f:
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
                            f"{email} is not a valid email address ({users_file}, line {i})"
                        )

                # Validate the role
                if not is_valid_role(role):
                    raise InitError(f"'{role}' is not a valid role ({users_file}, line {i})")

                users[email] = role
                i += 1
    else:
        # Show a warning - get_users does nothing
        warnings.warn("`get_users()` called with no user or users", RuntimeWarning)

    return users


def write_data(sheet, title, credentials=None):
    """Create COGS data files: config.tsv, sheet.tsv, and field.tsv."""
    # Create the "tracked" directory
    os.mkdir(".cogs/tracked")

    # Store COGS configuration
    with open(".cogs/config.tsv", "w") as f:
        writer = csv.DictWriter(f, delimiter="\t", lineterminator="\n", fieldnames=["Key", "Value"])
        v = get_version()
        writer.writerow({"Key": "COGS", "Value": "https://github.com/ontodev/cogs"})
        writer.writerow({"Key": "COGS Version", "Value": v})
        if credentials:
            writer.writerow({"Key": "Credentials", "Value": credentials})
        writer.writerow({"Key": "Title", "Value": title})
        writer.writerow({"Key": "Spreadsheet ID", "Value": sheet.id})

    # sheet.tsv contains sheet (table/tab) details from the spreadsheet
    with open(".cogs/sheet.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["ID", "Title", "Path", "Description", "Frozen Rows", "Frozen Columns",],
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

    # format.tsv contains all cells with formats -> format IDs
    with open(".cogs/format.tsv", "w") as f:
        writer = csv.DictWriter(
            f, delimiter="\t", lineterminator="\n", fieldnames=["Sheet Title", "Cell", "Format ID"],
        )
        writer.writeheader()

    with open(".cogs/formats.json", "w") as f:
        f.write(json.dumps(default_formats, sort_keys=True, indent=4))

    # note.tsv contains all cells with notes -> note
    with open(".cogs/note.tsv", "w") as f:
        writer = csv.DictWriter(
            f, delimiter="\t", lineterminator="\n", fieldnames=["Sheet Title", "Cell", "Note"],
        )
        writer.writeheader()

    with open(".cogs/validation.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["Sheet Title", "Range", "Condition", "Value"],
        )
        writer.writeheader()


def init(title, user=None, role="writer", users_file=None, credentials=None, verbose=False):
    """Init a new .cogs configuration directory in the current working directory. If one already
    exists, display an error message. Return True if project was created. Return False if a COGS
    project already exists in the directory."""
    set_logging(verbose)
    cwd = os.getcwd()
    if os.path.exists(".cogs"):
        # Do not raise CogsError, or else .cogs/ will be deleted
        logging.critical(f"COGS project already exists in {cwd}/.cogs/")
        return False

    logging.info(f"initializing COGS project '{title}' in {cwd}/.cogs/")
    os.mkdir(".cogs")

    # Process supplied users
    users = {}
    if user or users_file:
        users = get_users(user=user, role=role, users_file=users_file)

    # Create a Client to access API
    if credentials:
        # Use a credentials file
        gc = get_client(credentials_path=credentials)
    else:
        # Use environment vars
        gc = get_client()

    # Create the new Sheet
    try:
        spreadsheet = gc.create(title)
    except gspread.exceptions.APIError as e:
        raise InitError(f"Unable to create new spreadsheet '{title}'\n" f"CAUSE: {e.response.text}")

    # Share with each user
    for email, role in users.items():
        try:
            spreadsheet.share(email, perm_type="user", role=role)
        except gspread.exceptions.APIError as e:
            logging.error(f"Unable to share '{title}' with {email} as {role}\n" + e.response.text)

    # Write data to COGS directory
    write_data(spreadsheet, title, credentials=credentials)
    return True
