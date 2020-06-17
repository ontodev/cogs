# COGS Operates Google Sheets

**WARNING** This project is work in progress.

COGS takes a set of TSV files on your local file system and allows you to edit them using Google Sheets.


## Design

Since COGS is designed to synchronize local and remote sets of tables,
we try to follow the familiar `git` interface and workflow:

- `cogs init` creates a `.cogs/` directory to store configuration data and copies of the remote files
- `cogs create` creates a Google Sheet and stores the ID in `.cogs/`
- `cogs add foo.tsv` starts tracking the `foo.tsv` table
- `cogs push` pushes local tables to the Google Sheet
- `cogs fetch` fetches the data from the Goolgle Sheet and stores it in `.cogs/`
- `cogs status` summarizes the differences between tracked files and their copies in `.cogs/`
- `cogs diff` shows detailed differences between local files and the Google Sheet
- `cogs pull` overwrites local files with the data from the Google Sheet, if they have changed
- `cogs delete` destroys the Google Sheet, but leaves local files alone

There is no step corresponding to `git commit`.

### `init`

```
cogs init -c [path-to-credentials] -u [email] -r [role]
```

`init` **requires** [Google API credentials](https://gspread.readthedocs.io/en/latest/oauth2.html#enable-api-access-for-a-project) in JSON format to be used for all sheet operations (`-c`/`-credentials`). These credentials are used to create a [`gspread`](https://gspread.readthedocs.io/en/latest/) Client that can create, share, edit, and delete Google Sheets.

Optionally, you may provide a user email (`-u`/`--user`) that all sheets will be shared with when running `create`. By default, this user will have write access. You can also specify a role (`-r`/`--role`) to override this:
- `owner` (there can only be one owner of a sheet, and any time the `owner` role is specified, the ownership will be transferred to that user)
- `writer`
- `viewer`

You can also share with multiple users by providing the path to a TSV (`-U`, `--users`). Each line should have a user email and the role for that user, separated by a tab.

Six files are created in the `.cogs/` directory when running `init`:
- `config.tsv`: COGS configuration, including the sheet details once createdd
- `credentials.json`: Google API credentials (copied from `-c`/`--credentials`)
- `field.tsv`: Sheet field names (contains default COGS fields)
- `sheet.tsv`: Sheet names and details (empty)
- `table.tsv`: Table names and details (empty)
- `users.tsv`: User emails and roles (filled out from `-u`/`--user` and `-U`/`--users`)

### `create`

```
cogs create -t [title] -d [description]
```

Running `create` will create a new, empty, Google sheet with the given title (`-t`/`--title`). A description (`-d`/`--description`) is optional.

This sheet will automatically be shared with any users specified in `init` and these details will be added to `.cogs/sheet.tsv`.
