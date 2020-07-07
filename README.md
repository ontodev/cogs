# COGS Operates Google Sheets

**WARNING** This project is work in progress.

COGS takes a set of TSV files on your local file system and allows you to edit them using Google Sheets.


## Design

Since COGS is designed to synchronize local and remote sets of tables,
we try to follow the familiar `git` interface and workflow:

- [`cogs init`](#init) creates a `.cogs/` directory to store configuration data and creates a spreadsheet for the project
- [`cogs open`](#open) displays the URL of the spreadsheet
- [`cogs share`](#share) shares the spreadsheet with specified users
- [`cogs add foo.tsv`](#add) starts tracking the `foo.tsv` table as a sheet
- [`cogs rm foo.tsv`](#rm) stops tracking the `foo.tsv` table as a sheet
- [`cogs push`](#push) pushes changes to local sheets to the project spreadsheet
- `cogs fetch` fetches the data from the spreadsheet and stores it in `.cogs/`
- `cogs status` summarizes the differences between tracked files and their copies in `.cogs/`
- `cogs diff` shows detailed differences between local files and the spreadsheet
- `cogs pull` overwrites local files with the data from the spreadsheet, if they have changed
- [`cogs delete`](#delete) destroys the spreadsheet and configuration data, but leaves local files alone

There is no step corresponding to `git commit`.

## Definitions

- **Spreadsheet**: the remote Google Sheets spreadsheet - each COGS project corresponds to one spreadsheet
- **Sheet**: a tab in the spreadsheet - each sheet corresponds to one local TSV or CSV table

---

### Getting started development

Until we distribute COGS with Pypi, and for local development on Unix (Linux or macOS), we suggest these install instructions:

```
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
$ pip install -e .
$ cogs --help
```

### `init`

Running `init` creates a `.cogs` directory containing configuration data. This also creates a new Google Sheets spreadsheet and stores the ID. Optionally, this new sheet may be shared with users.

```
cogs init -c [path-to-credentials] -t [project-title] -u [email] -r [role]
```

Options:
- `-c`/`--credentials`: **required**, path to [Google API credentials](https://gspread.readthedocs.io/en/latest/oauth2.html#enable-api-access-for-a-project) in JSON format
- `-t`/`--title`: **required**, title of the project which will be used as the title of the Google spreadsheet
- `-u`/`--user`: email of the user to share the sheet with (if a `--role` is not specified, this user will be a writer)
- `-r`/`--role`: role of the user specified by `--user`: `writer` or `reader`
- `-U`/`--users`: path to TSV containing emails and roles for multiple users (header optional)

Three files are created in the `.cogs/` directory when running `init`:
- `config.tsv`: COGS configuration, including the spreadsheet details 
- `field.tsv`: Field names used in sheets (contains default COGS fields)
- `sheet.tsv`: Sheet names in spreadsheet and details (empty) - the sheets correspond to local tables

All other tasks will fail if a COGS project has not been initialized in the working directory.

---

### `open`

Running `open` displays the URL of the spreadsheet.

---

### `delete`

Running `delete` reads the configuration data in `.cogs/config.tsv` to retrieve the spreadsheet ID. This spreadsheet is deleted in Google Sheets and the `.cogs` directory containing all project data is also removed. Any local TSV/CSV tables specified as sheets in the spreadsheet are left untouched.

```
cogs delete
```

---

### `share`

Running `share` shares the spreadsheet with the specified user(s).
```
cogs share -r [reader-email] -w [writer-email]
```

There are three options:
- `-r`/`--reader`: email of the user to give read access to
- `-w`/`--writer`: email of the user to give write access to
- `-o`/`--owner`: email of the user to transfer ownership to

We **do not recommend** transferring ownership of the COGS project spreadsheet, as this will prevent COGS from performing any administrative actions (e.g., `cogs delete`). If you do transfer ownership and wish to delete the project, you should simply remove the `.cogs/` directory and then go online to Google Sheets and manually delete the project.

---

### `add`

Running `add` will begin tracking a local TSV or CSV table. The table details (path, name/title, and description) get added to `.cogs/sheet.tsv` and all headers are added to `.cogs/field.tsv`, if they do not already exist.

```
cogs add [path] -d "[description]"
```

The `-d`/`--description` is optional.

The sheet title is created from the path (e.g., `tables/foo.tsv` will be named `foo`). If a sheet with this title already exists in the project, the task will fail. The sheet/file name cannot be one of the COGS reserved names: `config`, `field`, `sheet`, or `user`.

This does not add the table to the spreadsheet as a sheet - use `cogs push` to push all tracked local tables to the project spreadsheet.

---

### `rm`

Running `rm` will stop tracking one or multiple local TSV table. They get removed from `.cogs/sheet.tsv`, and the `.cogs/field.tsv` is updated to remove the fields that were unique to those file.
```
cogs rm [paths]
```

This does not delete the table(s) from the spreadsheet as sheet(s) - use `cogs push` to push all tracked local tables to the project spreadsheet.

---

### `push`

Running `push` will sync the spreadsheet with your local changes. This includes creating new sheets for any added tables (`cogs add`) and deleting sheets for any removed tables (`cogs rm`). Any changes to the local tables are also pushed to the corresponding sheets.

```
cogs push
```
