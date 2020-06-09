# COGS Operates Google Sheets

**WARNING** This project is wok in progress.

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
