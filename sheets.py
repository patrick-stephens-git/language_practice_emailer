import logging
import gspread
from config import sheet_id, sheet_gid, google_credentials_file

logger = logging.getLogger(__name__)

COMMON_COLUMNS: dict[str, str] = {"yes": "Common? Yes", "no": "Common? No", "unsure": "Common? Unsure"}

def get_worksheet() -> gspread.Worksheet:
    client = gspread.service_account(filename=google_credentials_file) # Authenticates as the service account, not as a public viewer
    return client.open_by_key(sheet_id).get_worksheet_by_id(sheet_gid)

def record_common(word: str, is_common: str) -> None:
    try:
        column_name: str = COMMON_COLUMNS.get(is_common.strip().lower(), COMMON_COLUMNS["unsure"]) # Anything other than Yes/No is treated as Unsure
        ws = get_worksheet()
        headers: list[str] = ws.row_values(1)
        word_col: int = headers.index("Word") + 1 # gspread is 1-indexed
        target_col: int = headers.index(column_name) + 1
        cell = ws.find(word, in_column=word_col) # First exact match; the sheet has one row per word
        if cell is None:
            logger.error(f"Word '{word}' not found in sheet; {column_name} not updated.")
            return
        new_count: int = int(ws.cell(cell.row, target_col).value or 0) + 1 # Empty cell counts as 0
        ws.update_cell(cell.row, target_col, new_count)
        logger.info(f"Incremented '{column_name}' for '{word}' (row {cell.row}) to {new_count}.")
    except Exception as e: # Sheet problems must never break the daily run
        logger.exception(f"Failed to update Common? count for '{word}': {e}")
