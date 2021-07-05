# COGS Operates Google Sheets

**WARNING** This project is work in progress.

COGS takes a set of TSV files on your local file system and allows you to edit them using Google Sheets.


## Setup

COGS is distributed on [PyPI](https://pypi.org/project/ontodev-cogs/). To install:
```
pip install ontodev-cogs
```

To see a list of all commands:
```
cogs -h
```

For help with a specific command:
```
cogs [command] -h
```

#### Development

For local development on Unix (Linux or macOS), we suggest these install instructions:

```
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
$ pip install -e .
$ cogs -h
```

---

## Overview

Since COGS is designed to synchronize local and remote sets of tables,
we try to follow the familiar `git` interface and workflow:

- [`cogs init`](#init) creates a `.cogs/` directory to store configuration data and creates a spreadsheet for the project
- [`cogs add foo.tsv`](#add) starts tracking the `foo.tsv` table as a sheet
- [`cogs rm foo.tsv`](#rm) stops tracking the `foo.tsv` table as a sheet
- [`cogs push`](#push) pushes changes to local sheets to the project spreadsheet
- [`cogs fetch`](#fetch) fetches the data from the spreadsheet and stores it in `.cogs/`
- [`cogs ls`](#ls) shows a list of currently-tracked sheet names and their local names
- [`cogs status`](#status) summarizes the differences between tracked files and their copies in `.cogs/`
- [`cogs diff`](#diff) shows detailed differences between local files and the spreadsheet
- [`cogs merge`](#merge) overwrites local files with the data from the spreadsheet, if they have changed
- [`cogs pull`](#pull) combines fetch and merge

There are some other commands that do not correspond to any `git` actions:

- [`cogs apply`](#apply) applies attributes from standardized tables to one or more sheets
- [`cogs clear`](#clear) removes formatting, notes, and/or data validation rules from one or more sheets
- [`cogs connect`](#connect) initiates a new COGS project by connecting an existing Google Spreadsheet
- [`cogs delete`](#delete) destroys the spreadsheet and configuration data, but leaves local files alone
- [`cogs ignore`](#ignore) begins ignoring a tracked sheet so that the local copy is no longer updated
- [`cogs mv foo.tsv bar.tsv`](#mv) updates the path to the local version of a spreadsheet from `foo.tsv` to `bar.tsv`
- [`cogs open`](#open) displays the URL of the spreadsheet
- [`cogs share`](#share) shares the spreadsheet with specified users

There is no step corresponding to `git commit`.

We recommend running `cogs push` after updating a local tracked sheet to keep the remote sheets in sync.

When updating a remote sheet, we recommend the following to keep the local sheets in sync:
```
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
- **Format**: the format applied to a cell in a sheet (e.g., background color, font family, etc.)
- **Note**: a note (a.k.a. comment) on a cell that appears when hovered over in the sheet

---

## Commands

### `add`

Running `add` will begin tracking a local TSV or CSV table. The table details (path, name/title, and description) get added to `.cogs/sheet.tsv`.

```
cogs add [path] -d "[description]"
```

The `-d`/`--description` is optional. You can also specify a number of rows and or columns to freeze:

```
cogs add [path] -r [freeze_row] -c [freeze_column]
```

If you specify `-r 2 -c 1`, then the first two rows and the first column will be frozen once the sheet is pushed to the remote Google Spreadsheet. If these options are not included, no rows or columns will be frozen.

By default, the sheet title is created from the path (e.g. `tables/foo.tsv` will be named `foo`). If a sheet with this title already exists in the project, the task will fail.

You can also specify a sheet title that is different from the path with the `-t`/`--title` option:

```
cogs add [path] -t "[title]"
```

This does not immediately change the Google Sheet -- use `cogs push` to push all tracked local tables to the project spreadsheet.

If an added path does not exist, COGS will create an empty file at that location.

#### Adding an Ignored Sheet

By default, COGS ignores any untracked remote sheets. If you wish to start tracking a new remote sheet, you can do this by passing the sheet title to `add`:

```
cogs add [title]
```

The default path for pulling changes from this newly-added sheet will be the current working directory (the same directory as `.cogs/` is in) and will be a lowercase, space-replaced version of the title (e.g. `My Sheet` becomes `my_sheet.tsv`). If you already have a tracked sheet at this location, the date & time will be appended to the path (e.g., `my_sheet_20200922_103045.tsv` for a sheet fetched at 10:30:45 on 2020/09/22). This path can be updated with [`cogs mv`](#mv). Alternatively, if you want to specify a path immediately, you can:

```
cogs add [path] -t [title]
```

... where the "title" is the sheet title of the existing ignored sheet.

You can also add *all* ignored sheets using the `-a`/`--all` flag:

```
cogs add --all
```

We recommend running `cogs fetch` or `cogs pull` immediately after adding ignored sheets to sync your `.cogs` directory.

### `apply`

Running `apply` applies the details of one or more [message tables](#message-tables) or [data validation tables](#data-validation-tables) to the spreadsheet as cell formatting and notes.

```
cogs apply [table1.tsv table2.tsv ...]
```

#### Message Tables

Message tables provide a standard table output for logging messages (info, warn, or error) that can be converted into formatting and notes in the spreadsheet using `apply`. As long as the table follows the format described below, any type of message can be applied to the sheets. One example is the errors from [ROBOT template](http://robot.obolibrary.org/template).

These tables are applied to the sheets as formats and notes. The three levels of logging will be formatted with a black border and the following backgrounds:
* **error**: light red background
* **warn/warning**: light yellow background
* **info**: light blue background

The notes and formats will be added to any existing, but will take priority over the existing notes and formats.

These tables must have the following headers:
* **table**: name of the table that the problem occurs in
* **cell**: A1 format of problematic cell location

The following fields are optional:
* **level**: severity of the problem; error, warn, or info - if not included, this will default to "error"
* **rule ID**: an IRI or CURIE to uniquely identify the problem
* **rule**: descriptive name of the problem - this is converted to the cell note
* **message**: detailed instructions on how to fix the problem
* **suggestion**: a suggested value to replace the problematic value

The only required fields are `table` and `cell`. If no other fields are provided, the cell will be highlighted red with a note that says "ERROR". We strongly recommend using either a `rule ID` or `rule` to identify the message, and `message` text to provide more details.

#### Data Valildation Tables

The data validation tables are applied to the sheets as data validation rules. These tables must have the following headers:
* **table**: name of the table to add data validation rules to
* **range**: A1 format of the cell or range of cells to apply data validation rules to
* **condition**: the condition (see below) for the data validation rule
* **value**: the allowed value or values (see bellow)for the data validation rule

For example:

| table  | range | condition   | value         |
| ------ | ----- | ----------- | ------------- |
| Sheet1 | A2:A  | TEXT_EQ     | foo           |
| Sheet1 | B2:B  | ONE_OF_LIST | foo, bar, baz |

For full descriptions of each condition type, please see [Google Sheets API ConditionType](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/other#ConditionType).

Any value greater than one should be specified as a comma-separated list (e.g., for `NUMBER_BETWEEN`, the value could be `1, 10`). For "0" values, leave the `value` column empty.

* *Number Conditions*

| Condition                | Values |
| ------------------------ | ------ |
| `NUMBER_GREATER`         | 1      |
| `NUMBER_GREATER_THAN_EQ` | 1      |
| `NUMBER_LESS`            | 1      |
| `NUMBER_LESS_THAN_EQ`    | 1      |
| `NUMBER_EQ`              | 1      |
| `NUMBER_NOT_EQ`          | 1      |
| `NUMBER_BETWEEN`         | 2      |
| `NUMBER_NOT_BETWEEN`     | 2      |

* *Text Conditions*

| Condition           | Values |
| ------------------- | ------ |
| `TEXT_CONTAINS`     | 1      |
| `TEXT_NOT_CONTAINS` | 1      |
| `TEXT_STARTS_WITH`  | 1      |
| `TEXT_ENDS_WITH`    | 1      |
| `TEXT_EQ`           | 1      |
| `TEXT_IS_EMAIL`     | 0      |
| `TEXT_IS_URL`       | 0      |

* *Date Conditions*

Dates can be supplied in whatever format you like, but we recomment `YYYY-MM-DD`. You can also specify the exact day, a month (`MM-YYYY`), or just a year (`YYYY`). Relative dates (e.g. "today") are not currently supported.

| Condition           | Values |
| ------------------- | ------ |
| `DATE_EQ`           | 1      |
| `DATE_BEFORE`       | 1      |
| `DATE_AFTER`        | 1      |
| `DATE_ON_OR_BEFORE` | 1      |
| `DATE_ON_OR_AFTER`  | 1      |
| `DATE_BETWEEN`      | 2      |
| `DATE_NOT_BETWEEN`  | 2      |
| `DATE_IS_VALID`     | 0      |

* *One-of Conditions*

`ONE_OF_LIST` values should be supplied as a comma separated list. There should be at least two values in the list. For single values, use `TEXT_EQ` instead. If an item in your `ONE_OF_LIST` contains a comma, escape it with a backslash (e.g., `single value 1, multi-value 2\, 3` will resolve to two values in the list).

| Condition      | Values |
| -------------- | ------ |
| `ONE_OF_RANGE` | 1      |
| `ONE_OF_LIST`  | 2+     |

* *Other Conditions*

The `CUSTOM_FORMULA` value must be a formula that evaluates to TRUE or FALSE.

| Condition        | Values |
| ---------------- | ------ |
| `BLANK`          | 0      |
| `NOT_BLANK`      | 0      |
| `CUSTOM_FORMULA` | 1      |
| `BOOLEAN`        | 0      |

### `clear`

`clear` removes applied attributes (either from [`apply`](#apply) or manually added to the sheet remotely) from one or more sheets:

```
cogs clear [keyword] [sheet-title-1] [sheet-title-2] ...
```

The keyword must be one of:
* **formats**: sheet formatting
* **notes**: sheet notes
* **validation**: data validation rules
* **all**: formats, notes, and rules

After the keyword, you can supply zero or more sheet titles to remove attributes from. If no sheet titles are provided, the attribute(s) specified by the keyword will be removed from *all* sheets.

### `connect`

`connect` is similar to [`init`](#init) in that it creates a new COGS project in the current directory. Instead of creating a new Google Spreadsheet, though, it connects to an existing one that you have already created. In order to run `connect`, you must not have an existing COGS project in the directory. We also recommend that you are the owner of the Spreadsheet you are connecting, as you will need to transfer ownership to the service account defined in your credentials.

```
cogs connect -k [spreadsheet-url-or-key] -c [path-to-credentials]
```

The `--key`/`-k` argument accepts either the full sheet URL or just the key. You can find the spreadsheet key in the URL of the Google Spreadsheet:
```
https://docs.google.com/spreadsheets/d/[SPREADSHEET-KEY]/edit#gid=0
```

As with `init`, you may exclude the `-c` argument if you have your credentials defined in the environment variable `GOOGLE_CREDENTIALS`. Note that this variable must be the *contents* of the credentials file, not the path to the file.

After connecting to the existing spreadsheet, COGS will pause to ask you to share the Spreadsheet with the service email. It will provide a link to the sheet and the service email to share with. You can either give the service email "Editor" permissions, or transfer ownership.

To give "Editor" access:
1. Open the Google Spreadsheet in your browser
2. Click "Share" in the upper right corner
3. Enter in the provided service email, uncheck "Nofity people", and click "Send"
4. Return to the terminal and press ENTER to continue

To transfer ownership, click "Share" again and click the drop-down next to the service email and select "Make owner"

Please be aware that if you do not transfer ownership to the service account, `cogs delete` will not work. All other commands will work with just "Editor" access. If you do transfer ownership, you can always transfer ownership back to yourself using the [`share`](#share) command.

`connect` will automatically fetch the existing sheets from the remote Google Spreadsheet. To get the local copies, just run `cogs merge`.

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

This will download all sheets in the spreadsheet to that directory as `{sheet-title}.tsv` - this will overwrite the existing sheets in `.cogs/tracked/`, but will not overwrite the local versions specified by their path. Any sheets that have been added with `add` and then pushed to the remote sheet with `push` will be given their IDs in `.cogs/sheet.tsv`.

`.cogs/format.tsv` and `.cogs/note.tsv` are also updated for any cell formatting or notes on cells, respectively. Each unique format is given a numerical ID and is stored as [CellFormat JSON](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/cells#cellformat).

If a new sheet has been added to the Google spreadsheet, this sheet will be added to `.cogs/sheet.tsv` as an "ignored" sheet. While it appears in the sheets, it will not be downloaded and has no local path. If you wish to add an ignored sheet to tracking, use [`cogs add`](#adding-an-ignored-sheet).

To sync the local version of sheets with the data in `.cogs/`, run [`cogs merge`](#merge).

Note that if a sheet has been _renamed_ remotely, the old sheet title will be replaced with the new sheet title. Any changes made to the local file corresponding to the old title will not be synced with the remote spreadsheet. Instead, once you run `cogs merge`, a new sheet `{new-sheet-title}.tsv` will appear in the current working directory (the same as if a new sheet were created). It is the same as if you were to delete the old sheet remotely and create a new sheet remotely with the same contents. Use `cogs merge` to write the new path - the old local file will not be deleted.

### `ignore`

Running `ignore` on a given sheet title will start ignoring that sheet. This means that the cached copy of the sheet in the `.cogs/` directory is deleted, and the local version will no longer be updated when running `cogs pull`.

```
cogs ignore [sheet-title]
```

You may only run `ignore` on a sheet that you are already tracking. This will *not* remove either your local copy or the remote sheet.

### `init`

Running `init` creates a `.cogs` directory containing configuration data. This also creates a new Google Sheets spreadsheet and stores the ID. Optionally, this new sheet may be shared with users.

```
cogs init -c [path-to-credentials] -t [project-title] -u [email] -r [role]
```

`gspread` needs credentials to create a service account; you can either provide these with a file (`-c [path]`) or with an environment variable (`GOOGLE_CREDENTIALS`). The environment variable should be a string containing the contents of the credentials file. You must surround the contents with single quotes when setting this variable:

```
export GOOGLE_CREDENTIALS='{...}'
```

Options:
- `-t`/`--title`: **required**, title of the project which will be used as the title of the Google spreadsheet
- `-c`/`--credentials`: path to [Google API credentials](https://gspread.readthedocs.io/en/latest/oauth2.html#enable-api-access-for-a-project) in JSON format
- `-u`/`--user`: email of the user to share the sheet with (if a `--role` is not specified, this user will be a writer)
- `-r`/`--role`: role of the user specified by `--user`: `writer` or `reader`
- `-U`/`--users`: path to TSV containing emails and roles for multiple users (header optional)

The following files are created in the `.cogs/` directory when running `init`:
- `config.tsv`: COGS configuration, including the spreadsheet details 
- `format.tsv`: Sheet ID, cell location or range, and format IDs (the format for each format ID is stored as a JSON dictionary in `.cogs/formats.json`)
- `note.tsv`: Sheet ID, cell location, and note for all notes
- `sheet.tsv`: Sheet names in spreadsheet and details (empty) - the sheets correspond to local tables
- `validation.tsv`: Data validation conditions

All other tasks will fail if a COGS project has not been initialized in the working directory.

### `ls`

Running `ls` displays a list of tracked sheet names and their local paths, even if the local path does not yet exist.

```
cogs ls
```

### `open`

Running `open` displays the URL of the spreadsheet.

```
cogs open
```

### `pull`

Running `pull` will sync local sheets with remote sheets. This combines `cogs fetch` and `cogs merge` into one step.

```
cogs pull
```

Note that if you make changes to a local sheet without running `cogs push`, then run `cogs pull`, the local changes **will be overwritten**.

### `push`

Running `push` will sync the spreadsheet with your local changes. This includes creating new sheets for any added tables (`cogs add`) and deleting sheets for any removed tables (`cogs rm`). Any changes to the local tables are also pushed to the corresponding sheets.

```
cogs push
```

This will also push all notes and formatting from `.cogs/format.tsv` and `.cogs/note.tsv`.

### `merge`

Running `merge` will sync local sheets with remote sheets after running `cogs fetch`.

```
cogs merge
```

Note that if you make changes to a local sheet without running `cogs push`, then run `cogs fetch && cogs merge`, the local changes **will be overwritten**.

### `mv`

Running `mv` will update the path of a local sheet.

```
cogs mv [old_path] [new_path]
```

This will only change the local path, not the sheet title. If you also wish to rename the sheet, you can do this with the `-t`/`--title` option:

```
cogs mv [old_path] [new_path] -t [new_title]
```

We recommend running `cogs push` after `cogs mv` to keep the remote spreadsheet in sync.

### `rm`

Running `rm` will stop tracking one or more local sheets. This will delete all local copies of the included paths, unless you include the optional `-k`/`--keep` flag.
```
cogs rm path [path...] [-k]
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

Please be aware that transfering ownership of the Spreadsheet prevent COGS from performing any administrative actions (e.g., `cogs delete`). If you do transfer ownership and wish to delete the project, you should simply remove the `.cogs/` directory and then go online to Google Sheets and manually delete the project.

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
