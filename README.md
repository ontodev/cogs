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
- [`cogs fetch`](#fetch) fetches the data from the spreadsheet and stores it in `.cogs/`
- `cogs mv` updates the path to the local version of a spreadsheet
- `cogs status` summarizes the differences between tracked files and their copies in `.cogs/`
- [`cogs diff`](#diff) shows detailed differences between local files and the spreadsheet
- `cogs pull` overwrites local files with the data from the spreadsheet, if they have changed
- [`cogs delete`](#delete) destroys the spreadsheet and configuration data, but leaves local files alone

There is no step corresponding to `git commit`.

## Logging

To print info-level logging messages (error and critical level messages are always printed), run any command with the `-v`/`--verbose` flag:

```
cogs [command & opts] -v
```

Otherwise, most commands succeed silently.

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

Running `add` will begin tracking a local TSV or CSV table. The table details (path, name/title, and description) get added to `.cogs/sheet.tsv` and all headers are added to `.cogs/field.tsv`, if they do not already exist with the default datatype of `cogs:text` (text string).

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

---

### `fetch`

Running `fetch` will sync the local `.cogs/` directory with all remote spreadsheet changes.

```
cogs fetch
```

This will download all sheets in the spreadsheet to that directory as `{sheet-title}.tsv` - this will overwrite the existing sheets in `.cogs/`, but will not overwrite the local versions specified by their path. As the sheets are downloaded, the fields are checked against existing fields in `.cogs/field.tsv` and any new fields are added with the default datatype of `cogs:text` (text string). Any sheets that have been added with `add` and then pushed to the remote sheet with `push` will be given their IDs in `.cogs/sheet.tsv`.

If a new sheet has been added to the Google spreadsheet, this sheet will be downloaded and added to `.cogs/sheet.tsv`. The default path for pulling changes will be the current working directory (the same directory as `.cogs/` is in). This path can be updated with `cogs mv`.

To sync the local version of sheets with the data in `.cogs/`, run `cogs pull`.

---

### `diff`

Running `diff` will display all file changes between local and remote sheets after running `cogs fetch`.

```
cogs diff
```

By default, this will display all files with changes. If you wish to just see the changes for one or more paths, you can provide those paths:

```
cogs diff path1.tsv path2.tsv ...
```

`diff` opens a responsive scrolling window. To scroll down, press the down arrow. To scroll up, press the up arrow (see all navigation below). For large files with many columns, you can also scroll to the right with the right arrow and back to the left with the left arrow.

The start of a diff for a sheet begins in bold with the file name (local and remote versions).

The displayed text below has formatting for changes between the local and remote sheets:
* Lines that have been _removed_ from the remote version of the sheet are in red text and begin with `---`.
* Lines that have been _added_ to the local version of the sheet are in green text and begin with `+++`.
* Lines that have been _changed_ between the remote and local versions are in blue text and begin with `->`.

In cells with _changed_ values, the cell is formatted as so:
```
old text -> new text
```

If a sheet has been newly created or deleted, these changes will not appear in `diff`. Instead, use `cogs status`.

To navigate the diff:
* &#8593;: move one line up
* &#8595;: move one line down
* &#8594;: move 20 characters right
* &#8592;: move 20 characters left
* `q`: quit
* `t`: go to top (first line)
* `b`: go to bottom (last line)
* `r`: go to rightmost characters (last column)
* `l`: to to leftmost characters (first column)
