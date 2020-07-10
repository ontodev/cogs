# COGS Operates Google Sheets

**WARNING** This project is work in progress.

COGS takes a set of TSV files on your local file system and allows you to edit them using Google Sheets.


## Overview

Since COGS is designed to synchronize local and remote sets of tables,
we try to follow the familiar `git` interface and workflow:

- [`cogs init`](#init) creates a `.cogs/` directory to store configuration data and creates a spreadsheet for the project
- [`cogs open`](#open) displays the URL of the spreadsheet
- [`cogs share`](#share) shares the spreadsheet with specified users
- [`cogs add foo.tsv`](#add) starts tracking the `foo.tsv` table as a sheet
- [`cogs rm foo.tsv`](#rm) stops tracking the `foo.tsv` table as a sheet
- [`cogs push`](#push) pushes changes to local sheets to the project spreadsheet
- [`cogs fetch`](#fetch) fetches the data from the spreadsheet and stores it in `.cogs/`
- [`cogs mv foo.tsv bar.tsv`](#mv) updates the path to the local version of a spreadsheet from `foo.tsv` to `bar.tsv`
- [`cogs status`](#status) summarizes the differences between tracked files and their copies in `.cogs/`
- [`cogs diff`](#diff) shows detailed differences between local files and the spreadsheet
- [`cogs pull`](#pull) overwrites local files with the data from the spreadsheet, if they have changed
- [`cogs delete`](#delete) destroys the spreadsheet and configuration data, but leaves local files alone

There is no step corresponding to `git commit`.

We recommend running `cogs push` after updating a local tracked sheet to keep the remote sheets in sync.

When updating a remote sheet, we recommend the following to keep the local sheets in sync:
```
cogs fetch
cogs pull
```

### Logging

To print info-level logging messages (error and critical level messages are always printed), run any command with the `-v`/`--verbose` flag:

```
cogs [command & opts] -v
```

Otherwise, most commands succeed silently.

### Definitions

- **Spreadsheet**: the remote Google Sheets spreadsheet - each COGS project corresponds to one spreadsheet
- **Sheet**: a tab in the spreadsheet - each sheet corresponds to one local TSV or CSV table
- **Remote**: data from Google Sheets
- **Local**: data from your local working directory
- **Cached**: data stored in `.cogs/` which is fetched from the remote spreadsheet

---

## Development

Until we distribute COGS with Pypi, and for local development on Unix (Linux or macOS), we suggest these install instructions:

```
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
$ pip install -e .
$ cogs --help
```

---

## Commands

### `add`

Running `add` will begin tracking a local TSV or CSV table. The table details (path, name/title, and description) get added to `.cogs/sheet.tsv` and all headers are added to `.cogs/field.tsv`, if they do not already exist with the default datatype of `cogs:text` (text string).

```
cogs add [path] -d "[description]"
```

The `-d`/`--description` is optional.

The sheet title is created from the path (e.g., `tables/foo.tsv` will be named `foo`). If a sheet with this title already exists in the project, the task will fail. The sheet/file name cannot be one of the COGS reserved names: `config`, `field`, `sheet`, `renamed`, or `user`.

This does not add the table to the spreadsheet as a sheet - use `cogs push` to push all tracked local tables to the project spreadsheet.

### `delete`

Running `delete` reads the configuration data in `.cogs/config.tsv` to retrieve the spreadsheet ID. This spreadsheet is deleted in Google Sheets and the `.cogs` directory containing all project data is also removed. Any local TSV/CSV tables specified as sheets in the spreadsheet are left untouched.

```
cogs delete
```

### `diff`

Running `diff` will display all file changes between local and remote sheets after running `cogs fetch` or after updating a local sheet (before pushing or pulling those changes).

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

### `fetch`

Running `fetch` will sync the local `.cogs/` directory with all remote spreadsheet changes.

```
cogs fetch
```

This will download all sheets in the spreadsheet to that directory as `{sheet-title}.tsv` - this will overwrite the existing sheets in `.cogs/`, but will not overwrite the local versions specified by their path. As the sheets are downloaded, the fields are checked against existing fields in `.cogs/field.tsv` and any new fields are added with the default datatype of `cogs:text` (text string). Any sheets that have been added with `add` and then pushed to the remote sheet with `push` will be given their IDs in `.cogs/sheet.tsv`.

If a new sheet has been added to the Google spreadsheet, this sheet will be downloaded and added to `.cogs/sheet.tsv`. The default path for pulling changes will be the current working directory (the same directory as `.cogs/` is in). This path can be updated with `cogs mv`.

To sync the local version of sheets with the data in `.cogs/`, run `cogs pull`.

Note that if a sheet has been _renamed_ remotely, the old sheet title will be replaced with the new sheet title. Any changes made to the local file corresponding to the old title will not be synced with the remote spreadsheet. Instead, once you run `cogs pull`, a new sheet `{new-sheet-title}.tsv` will appear in the current working directory (the same as if a new sheet were created). It is the same as if you were to delete the old sheet remotely and create a new sheet remotely with the same contents. Use `cogs pull` to write the new path - the old local file will not be deleted.

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

### `open`

Running `open` displays the URL of the spreadsheet.

```
cogs open
```

### `pull`

Running `pull` will sync local sheets with remote sheets after running `cogs fetch`.

```
cogs pull
```

Note that if you make changes to a local sheet without running `cogs push`, then run `cogs fetch` and `cogs pull`, the local changes **will be overwritten**.

### `push`

Running `push` will sync the spreadsheet with your local changes. This includes creating new sheets for any added tables (`cogs add`) and deleting sheets for any removed tables (`cogs rm`). Any changes to the local tables are also pushed to the corresponding sheets.

```
cogs push
```

### `mv`

Running `mv` will update the path of a local sheet.

```
cogs mv [old_path] [new_path]
```

The old path must exist as a local file. It will be renamed to the new path during this process. If the basename of the new path (e.g., `tables/foo.tsv` -> `foo`) is already a tracked sheet, this command will fail as you cannot have two sheets with the same name.

We recommend running `cogs push` after `cogs mv` to keep the remote spreadsheet in sync.

### `rm`

Running `rm` will stop tracking one or more local sheets. They are removed from `.cogs/sheet.tsv`, and the `.cogs/field.tsv` is updated to remove the fields that were unique to those sheets. Additionally, this does not delete any local copies of sheets specified by their paths.
```
cogs rm [paths]
```

This does not delete the sheet(s) from the spreadsheet - use `cogs push` to push all local changes to the remote spreadsheet and remove cached data about the sheet.

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

### `status`

Running `status` shows the difference between local and remote copies of tracked sheets.

```
cogs status
```

There are five kinds of statuses (note that any changes to the remote spreadsheet will not be accounted for until you run `cogs fetch`)
* **Modified locally**: the sheet exists both locally and remotely (cached), but the local version has been edited since the last time `cogs fetch` or `cogs push` were run
    * use `cogs diff [path]` to see details
	* use `cogs push` to sync local changes to remote version (overwriting any changes to remote not yet pulled)
* **Modified remotely**: the sheet exists both locally and remotely, but `cogs fetch` has been run and returned a modified sheet since the last time the local version was edited
    * use `cogs diff [path]` to see details
    * use `cogs pull` to sync remote changes to local version (overwriting any changes to local not yet pushed)
* **Added locally**: the sheet exists locally and has been added to tracking, but is not yet pushed to the remote spreadsheet
    * use `cogs push` to add the sheet to the remote spreadsheet
* **Added remotely**: the sheet exists remotely and has been added to tracking, but is not yet pulled to a local copy
    * use `cogs pull` to add the sheet to locally
* **Removed locally**: the sheet exists remotely but has been removed from tracking using `cogs rm`
    * use `cogs push` to remove the sheet from the remote spreadsheet
* **Removed remotely**: the sheet exists locally but has been removed from remote spreadsheet
    * use `cogs pull` to remove the sheet locally
