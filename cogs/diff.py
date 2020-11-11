import curses
import os
import re
import tabulate

from cogs.exceptions import DiffError
from cogs.helpers import get_diff, get_tracked_sheets, set_logging, validate_cogs_project


def close_screen(stdscr):
    """Reset curses options and end window."""
    # Clean up window
    stdscr.keypad(False)
    curses.nocbreak()
    curses.echo()
    curses.endwin()


def get_diff_lines(cogs_dir, diffs, sheet_details):
    """Return the lines for a diff as an array of pairs (text, formatting)."""
    lines = []
    for sheet_title, sheet_diff in diffs.items():
        details = sheet_details[sheet_title]
        path_name = re.sub(r"[^A-Za-z0-9]+", "_", sheet_title.lower())
        remote = f"{cogs_dir}/tracked/{path_name}.tsv"
        local = details["Path"]
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
    return lines


def display_diff(cogs_dir, diffs, sheets):
    """Display an interactive curses screen with the formatted daff diff lines."""
    # Init the curses screen
    stdscr = curses.initscr()

    # Set screen/curses options
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)
    stdscr.keypad(True)
    stdscr.scrollok(True)

    # Set the color pairs
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_CYAN, -1)

    # Get the lines to display
    lines = get_diff_lines(cogs_dir, diffs, sheets)

    if not lines:
        # Nothing to display
        close_screen(stdscr)
        return None

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
            stdscr.clear()
            stdscr.refresh()

            # Get the lines to display based on current top line & size of window
            disp_lines = lines[y : y + rows]

            # Display these lines, only printing ot the size of the cols (x)
            max_x = 0
            for i in range(0, len(disp_lines)):
                text = disp_lines[i][0].rstrip()
                if len(text) > max_x:
                    max_x = len(text)
                text = text[x : cols + x]
                fmt = disp_lines[i][1]
                if fmt:
                    stdscr.addstr(i, 0, text + "\n", fmt)
                else:
                    stdscr.addstr(i, 0, text + "\n")

            # Add a message when we hit the EOF
            if eof or rows > len(lines) - 2:
                stdscr.addstr(rows - 1, 0, "~ end of diff", curses.color_pair(3) | curses.A_BOLD)

            # Display current position in diff
            if max_x < cols + x:
                disp_x_num = max_x
            else:
                disp_x_num = cols + x

            if len(disp_lines) < rows + x:
                disp_y_num = len(disp_lines)
            else:
                disp_y_num = rows + y
            stdscr.addstr(
                rows,
                0,
                f"L{y}-{disp_y_num} of {len(lines)}, C{x}-{disp_x_num} of {max_x} | "
                f"q = quit, t = top, b = bottom, l = leftmost, r = rightmost",
            )

            # Get user input
            k = stdscr.getch()
            if k == ord("q"):
                # Exit
                return diffs
            elif k == ord("l"):
                # Leftmost
                x = 0
                continue
            elif k == ord("t"):
                # Top
                eof = False
                y = 0
                continue
            elif k == ord("r"):
                # Rightmost
                if not cols > max_x:
                    x = max_x - cols + 1
                continue
            elif k == ord("b"):
                # Bottom
                if not eof and not disp_y_num == len(lines):
                    eof = True
                    y = len(lines) - rows
                continue
            elif k == curses.KEY_DOWN:
                if disp_y_num == len(lines):
                    eof = True
                elif not eof:
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
                if x + cols < max_x:
                    x += 20
                continue
            elif k == curses.KEY_LEFT:
                if x > 0:
                    x -= 20
                continue
    finally:
        close_screen(stdscr)
    return diffs


def diff(paths=None, use_screen=True, verbose=False):
    """Return a dict of sheet title to daff diff lines. If no paths are provided, diff over all
    sheets in the project. If use_screen, display an interactive curses screen with the diffs."""
    set_logging(verbose)
    cogs_dir = validate_cogs_project()

    sheets = get_tracked_sheets(cogs_dir)
    tracked_paths = [details["Path"] for details in sheets.values()]
    if paths:
        # Update sheets to diff
        for p in paths:
            if p not in tracked_paths:
                raise DiffError(f"sheet '{p}' is not part of the current project")
        sheets = {
            sheet_title: details
            for sheet_title, details in sheets.items()
            if details["Path"] in paths
        }

    diffs = {}
    for sheet_title, details in sheets.items():
        path_name = re.sub(r"[^A-Za-z0-9]+", "_", sheet_title.lower())
        remote = f"{cogs_dir}/tracked/{path_name}.tsv"
        local = details["Path"]
        if os.path.exists(local) and os.path.exists(remote):
            sheet_diff = get_diff(local, remote)
            diffs[sheet_title] = sheet_diff

    if not diffs:
        return None

    if use_screen:
        return display_diff(cogs_dir, diffs, sheets)

    return diffs
