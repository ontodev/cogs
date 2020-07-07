import curses
import logging
import os
import sys
import tabulate

from cogs.exceptions import CogsError, DiffError
from cogs.helpers import get_diff, get_sheets, set_logging, validate_cogs_project


def get_lines(sheets):
    """Return the lines for a diff as an array of pairs (text, formatting)."""
    lines = []
    for sheet_title, details in sheets.items():
        remote = f".cogs/{sheet_title}.tsv"
        local = details["Path"]
        if os.path.exists(local) and os.path.exists(remote):
            sheet_diff = get_diff(local, remote)
            if len(sheet_diff) > 1:
                lines.append(("", None))
                lines.append((f"--- {remote} (remote)", curses.A_BOLD))
                lines.append((f"+++ {local} (local)", curses.A_BOLD))
                has_col_changes = True
                for c in set(sheet_diff[1]):
                    if c != "+++" and c != "---":
                        has_col_changes = False
                        break
                if has_col_changes:
                    hs1 = sheet_diff.pop(0)
                    hs2 = sheet_diff.pop(0)
                    headers = []
                    for idx in range(0, len(hs1)):
                        h1 = hs1[idx]
                        if h1 == "!":
                            headers.append("")
                        else:
                            h2 = hs2[idx]
                            headers.append(f"{h1}\n{h2}")
                else:
                    headers = sheet_diff.pop(0)
                    headers[0] = ""
                tab = tabulate.tabulate(sheet_diff, headers=headers)
                for t in tab.split("\n"):
                    if t.startswith("+++"):
                        lines.append((t, curses.color_pair(2)))
                    elif t.startswith("---") and not t.endswith("---"):
                        lines.append((t, curses.color_pair(1)))
                    elif t.startswith("->"):
                        lines.append((t, curses.color_pair(3)))
                    else:
                        lines.append((t, None))

        # TODO - handle created and deleted sheets based on add/rm
        #      - and based on new sheets from fetch
    return lines


def diff(args):
    """Start a window with dynamic response to display the diffs for all provided paths."""
    set_logging(args.verbose)
    validate_cogs_project()

    sheets = get_sheets()
    paths = [details["Path"] for details in sheets.values()]
    if args.paths:
        for p in args.paths:
            if p not in paths:
                raise DiffError(f"sheet '{p}' is not part of the current project")
        sheets = {
            sheet_title: details
            for sheet_title, details in sheets.items()
            if details["Path"] in args.paths
        }

    # Init the curses screen
    stdscr = curses.initscr()

    # Set screen/curses options
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.scrollok(True)

    # Set the color pairs
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_CYAN, -1)

    # Get lines for the diff display
    lines = get_lines(sheets)

    try:
        stdscr.clear()
        stdscr.refresh()

        # Get the size of the window
        rows, cols = stdscr.getmaxyx()
        rows = rows - 1

        # Tracking for current x and y
        # Row is y and col position is x
        y = 0
        x = 0
        eof = False

        # Display lines
        while True:
            # Add a message when we hit the EOF
            if eof or rows > len(lines) - 2:
                stdscr.addstr(
                    rows, 0, "~ end of diff", curses.color_pair(3) | curses.A_BOLD
                )

            # Get the lines to display based on current top line & size of window
            disp_lines = lines[y : y + rows]

            # Display these lines, only printing ot the size of the cols (x)
            for i in range(0, len(disp_lines)):
                text = disp_lines[i][0][x: cols + x]
                fmt = disp_lines[i][1]
                if fmt:
                    stdscr.addstr(i, 0, text + "\n", fmt)
                else:
                    stdscr.addstr(i, 0, text + "\n")

            # Get user input
            k = stdscr.getch()
            if k == ord("q"):
                # Exit
                return
            elif k == curses.KEY_DOWN:
                if not eof and not rows > len(lines) - 2:
                    y += 1
                    if y + rows == len(lines) + 1:
                        eof = True
                continue
            elif k == curses.KEY_UP:
                if eof:
                    eof = False
                if y > 0:
                    y -= 1
                continue
            elif k == curses.KEY_RIGHT:
                x += 20
                continue
            elif k == curses.KEY_LEFT:
                if x > 0:
                    x -= 20
                continue

    finally:
        # Clean up window
        stdscr.keypad(False)
        curses.nocbreak()
        curses.echo()
        curses.endwin()


def run(args):
    """Wrapper for diff function."""
    try:
        diff(args)
    except CogsError as e:
        logging.critical(str(e))
        sys.exit(1)
