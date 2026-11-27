import logging
import pandas as pd
from sheets import get_worksheet
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

def get_word() -> tuple[str, str, list[str]]:
    #####################################
    ## Read File (authenticated, so the sheet can stay private):
    df = pd.DataFrame(get_worksheet().get_all_records()).replace("", pd.NA) # blank cells become NA

    logger.info(f"How many rows in df: {len(df)}")
    logger.info(f"How many unique words in df: {df['Word'].nunique()}")

    #####################################
    ## Data Prep:
    all_words: list[str] = df["Word"].dropna().unique().tolist() # Full word list captured before Lookup Count expansion, used later to filter LLM-generated synonyms already in the spreadsheet
    df = df.loc[df.index.repeat(df["Lookup Count"])] # Expand count of rows by the number in the "Lookup Count" column so that it's more likely to send words that are often reviewed (words looked up once still get a single entry)
    row = df.sample(n=1).iloc[0] # Randomly select 1 row
    sample_word: str = row["Word"]
    sample_translation: str = "" if pd.isna(row["Translation"]) else row["Translation"] # blank cell
    logger.info(f"Word: {sample_word}")
    logger.info(f"Translation: {sample_translation}")
    return sample_word, sample_translation, all_words

if __name__ == '__main__':
    setup_logging()
    get_word()