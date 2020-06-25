# COGS Operates Google Sheets

**WARNING** This project is work in progress.

COGS takes a set of TSV files on your local file system and allows you to edit them using Google Sheets.


## Design

Since COGS is designed to synchronize local and remote sets of tables,
we try to follow the familiar `git` interface and workflow:

- [`cogs init`](#init) creates a `.cogs/` directory to store configuration data and creates a Google Sheet for the project
- [`cogs share`](#share) shares the Google Sheet with specified users
- [`cogs add foo.tsv`](#add) starts tracking the `foo.tsv` table
- `cogs push` pushes local tables to the Google Sheet
- `cogs fetch` fetches the data from the Goolgle Sheet and stores it in `.cogs/`
- `cogs status` summarizes the differences between tracked files and their copies in `.cogs/`
- `cogs diff` shows detailed differences between local files and the Google Sheet
- `cogs pull` overwrites local files with the data from the Google Sheet, if they have changed
- [`cogs delete`](#delete) destroys the Google Sheet and configuration data, but leaves local files alone

There is no step corresponding to `git commit`.

---

### `init`

Running `init` creates a `.cogs` directory containing configuration data. This also creates a new Google Sheet and stores the Sheet ID. Optionally, this new sheet may be shared with users.

```
cogs init -c [path-to-credentials] -t [project-title] -u [email] -r [role]
```

Options:
- `-c`/`--credentials`: **required**, path to Google API credentials](https://gspread.readthedocs.io/en/latest/oauth2.html#enable-api-access-for-a-project) in JSON format
- `-t`/`--title`: **required**, title of the project which will be used as the title of the Google Sheet
- `-u`/`--user`: email of the user to share the sheet with (if a `--role` is not specified, this user will be a writer)
- `-r`/`--role`: role of the user specified by `--user`: `writer` or `reader`
- `-U`/`--users`: path to TSV containing emails and roles for multiple users (header optional)

Three files are created in the `.cogs/` directory when running `init`:
- `config.tsv`: COGS configuration, including the Sheet details 
- `field.tsv`: Field names used in tables (contains default COGS fields)
- `sheet.tsv`: Table names in Sheet and details (empty) - the tables correspond to tabs in the Sheet

All other tasks will fail if a COGS project has not been initialized in the working directory.

---

### `delete`

Running `delete` reads the configuration data in `.cogs/config.tsv` to retrieve the Google Sheet ID. This Google Sheet is deleted, and the `.cogs` directory containing all project data is also removed. Any TSVs specified as tables in the Sheet are left untouched.

```
cogs delete
```

---

### `share`

Running `share` shares the Google Sheet with the specified user(s).
```
cogs share -r [reader-email] -w [writer-email]
```

There are three options:
- `-r`/`--reader`: email of the user to give read access to
- `-w`/`--writer`: email of the user to give write access to
- `-o`/`--owner`: email of the user to transfer ownership to

We **do not recommend** transferring ownership of the COGS project Sheet, as this will prevent COGS from performing any administrative actions (e.g., `cogs delete`). If you do transfer ownership and wish to delete the project, you should simply remove the `.cogs/` directory and then go online to Google Sheets and manually delete the project Sheet.

---

### `add`

Running `add` will begin tracking a local TSV or CSV table. The table details (path, name/title, and description) get added to `.cogs/sheet.tsv` and all headers are added to `.cogs/field.tsv`, if they do not already exist.

```
cogs add [path] -d "[description]"
```

The `-d`/`--description` is optional.

The table title is created from the path (e.g., `tables/foo.tsv` will be named `foo`). If a table with this title already exists in the project, the task will fail.

This does not add the table to the Google Sheet - use `cogs push` to push all tracked local tables to the project Sheet.
