import logging
import sys
from datetime import datetime, time
from time import perf_counter
from pull_data import get_word
from generate_response import response_generation
from synonym_filter import filter_known_synonyms
from emailer import emailer
from sheets import record_common
from config import run_count, target_country
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

ACTIVE_WINDOW_START: time = time(7, 0) # 7:00 AM local
ACTIVE_WINDOW_END: time = time(23, 5) # 10:05 PM local

def main() -> None:
    now: time = datetime.now().time() # Local machine time; checked before any other work, including logging setup
    if not (ACTIVE_WINDOW_START <= now <= ACTIVE_WINDOW_END):
        print(f"Outside active window ({ACTIVE_WINDOW_START}-{ACTIVE_WINDOW_END}); current local time is {now}. Skipping.")
        return

    setup_logging() # Initialize logging; runs after the window check so a skipped trigger does not overwrite the last run's log
    logger.info(f"Cron trigger started: run_count={run_count}, target country={target_country}.")
    failed_count: int = 0
    for run_number in range(1, run_count + 1):
        logger.info(f"Starting run {run_number} of {run_count}.")
        started: float = perf_counter()
        try: # one failed run must not stop the remaining runs
            sent: bool = send_practice_email()
        except Exception:
            logger.exception(f"Run {run_number} of {run_count} crashed.")
            sent = False
        failed_count += not sent
        logger.info(f"Run {run_number} of {run_count} {'sent' if sent else 'failed'} after {perf_counter() - started:.1f}s.")
    logger.info(f"Finished: {run_count - failed_count} sent, {failed_count} failed.")
    if failed_count:
        sys.exit(1)

def send_practice_email() -> bool:
    sample_word, sample_translation, all_words = get_word() # Fetch a random word, its spreadsheet translation, and the full spreadsheet word list
    ai_translation, example_synonyms, example_sentence, is_common, is_common_reason = response_generation(sample_word, sample_translation) # Generate all AI responses
    example_synonyms = filter_known_synonyms(example_synonyms, all_words) # Python-only step: drop any LLM-generated synonyms already present in the spreadsheet
    sent: bool = emailer(sample_word, sample_translation, ai_translation, example_sentence, example_synonyms, is_common, is_common_reason) # Send the email
    record_common(sample_word, is_common) # Tally the Common? Yes/No/Unsure answer in the spreadsheet; runs last so a sheet error can never block the email
    return sent

if __name__ == '__main__':
    main()
