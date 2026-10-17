"""The workbook look: a navy header row in bold white, centred, bordered, with
columns wide enough that nothing is cut off.

    workbook, sheet = excel_style.new_workbook("PPRA Tenders")
    ...append rows...
    excel_style.format_excel_headers(sheet, auto_filter=True)

Nothing here touches values other than to make them writable: control characters
Excel rejects are stripped, and a cell over Excel's hard 32,767-character limit
is truncated with a marker.
"""

from __future__ import annotations

from typing import Any

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

# -- the standard ------------------------------------------------------------

#: Header fill — Office's "Blue, Accent 1, Darker 50%".
HEADER_COLOR = "1F4E78"
#: Thin cell rule, light enough not to compete with the text.
BORDER_COLOR = "D5DDE5"
#: Header row height, in points.
HEADER_HEIGHT = 26

HEADER_FILL = PatternFill("solid", fgColor=HEADER_COLOR)
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)

_EDGE = Side(style="thin", color=BORDER_COLOR)
CELL_BORDER = Border(left=_EDGE, right=_EDGE, top=_EDGE, bottom=_EDGE)

# Column auto-fit bounds. The padding keeps the widest value clear of the column
# edge; the cap stops one long description from pushing every other column off
# the screen (that cell wraps instead).
WIDTH_PADDING = 4
MIN_WIDTH = 10
MAX_WIDTH = 60

# Excel refuses a cell over 32,767 characters. Long descriptions and extracted
# document text routinely exceed it; the untruncated value is in the DB.
MAX_CELL_CHARS = 32000
TRUNCATION_MARKER = " …[truncated]"


# -- cell values -------------------------------------------------------------


def sanitize_cell(value: Any) -> Any:
    """Make `value` writable by Excel, changing nothing else.

    Strips the control characters openpyxl refuses (portal text carries them
    surprisingly often) and truncates past Excel's hard cell limit. Non-strings
    — dates, numbers, None — are returned untouched so their cell keeps its
    type.
    """
    if not isinstance(value, str):
        return value
    value = ILLEGAL_CHARACTERS_RE.sub("", value)
    if len(value) > MAX_CELL_CHARS:
        value = value[:MAX_CELL_CHARS] + TRUNCATION_MARKER
    return value


# -- styling -----------------------------------------------------------------


def style_header_row(
    sheet: Worksheet,
    row: int = 1,
    first_column: int = 1,
    last_column: int | None = None,
) -> None:
    """Apply the standard header look to one row of `sheet`.

    Defaults to row 1 across every column that row uses.
    """
    last_column = last_column or sheet.max_column
    for column in range(first_column, last_column + 1):
        cell = sheet.cell(row=row, column=column)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGN
        cell.border = CELL_BORDER
    sheet.row_dimensions[row].height = HEADER_HEIGHT


def autofit_columns(
    sheet: Worksheet,
    min_width: int = MIN_WIDTH,
    max_width: int = MAX_WIDTH,
    padding: int = WIDTH_PADDING,
) -> None:
    """Size every column to its longest value, plus padding.

    Cells that anchor a merged range are ignored: a full-width banner merged
    across the sheet would otherwise set column A to the banner's own length and
    leave every other column at its minimum.
    """
    merged_anchors = {str(rng).split(":")[0] for rng in sheet.merged_cells.ranges}
    # Indexed rather than taken off the cells: a merged range fills its span with
    # MergedCell placeholders, which carry no column letter of their own.
    for index, column in enumerate(sheet.iter_cols(), start=1):
        longest = 0
        for cell in column:
            if cell.value is None or cell.coordinate in merged_anchors:
                continue
            # A wrapped multi-line value is only ever as wide as its widest line.
            for line in str(cell.value).splitlines() or [""]:
                longest = max(longest, len(line))
        sheet.column_dimensions[get_column_letter(index)].width = min(
            max(longest + padding, min_width), max_width
        )


def format_excel_headers(
    sheet: Worksheet,
    header_row: int = 1,
    autofit: bool = True,
    freeze: bool = True,
    auto_filter: bool = False,
) -> None:
    """The one call a finished sheet needs: style its header row and fit its
    columns.

    `freeze` pins the header row so it stays visible while scrolling; pass False
    for a sheet whose headers repeat (there is no single row to pin).
    `auto_filter` adds Excel auto-filtering dropdowns across the header row.
    """
    if sheet.max_row >= header_row:
        style_header_row(sheet, header_row)
    if autofit:
        autofit_columns(sheet)
    if freeze:
        sheet.freeze_panes = sheet.cell(row=header_row + 1, column=1).coordinate
    if auto_filter and sheet.max_row >= header_row:
        first_col = get_column_letter(1)
        last_col = get_column_letter(sheet.max_column)
        sheet.auto_filter.ref = f"{first_col}{header_row}:{last_col}{sheet.max_row}"


# -- whole sheets ------------------------------------------------------------


def new_workbook(title: str) -> tuple[Workbook, Worksheet]:
    """A workbook and its first sheet, named. Saves every export the same two
    lines of boilerplate."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title
    return workbook, sheet
