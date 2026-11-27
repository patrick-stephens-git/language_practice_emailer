from datetime import datetime, time
from pull_data import get_word
from generate_response import response_generation
from synonym_filter import filter_known_synonyms
from emailer import emailer
from sheets import record_common
from config import run_count
from utils.logging_config import setup_logging

ACTIVE_WINDOW_START: time = time(7, 0) # 7:00 AM local
ACTIVE_WINDOW_END: time = time(23, 5) # 10:05 PM local

def main() -> None:
    now: time = datetime.now().time() # Local machine time; checked before any other work, including logging setup
    if not (ACTIVE_WINDOW_START <= now <= ACTIVE_WINDOW_END):
        print(f"Outside active window ({ACTIVE_WINDOW_START}-{ACTIVE_WINDOW_END}); current local time is {now}. Skipping.")
        return

    logger = setup_logging() # Initialize logging
    for run_number in range(1, run_count + 1):
        logger.info(f"Starting run {run_number} of {run_count}.")
        send_practice_email()

def send_practice_email() -> None:
    sample_word, sample_translation, all_words = get_word() # Fetch a random word, its spreadsheet translation, and the full spreadsheet word list
    ai_translation, example_synonyms, example_sentence, is_common, is_common_reason = response_generation(sample_word, sample_translation) # Generate all AI responses
    example_synonyms = filter_known_synonyms(example_synonyms, all_words) # Python-only step: drop any LLM-generated synonyms already present in the spreadsheet
    emailer(sample_word, sample_translation, ai_translation, example_sentence, example_synonyms, is_common, is_common_reason) # Send the email
    record_common(sample_word, is_common) # Tally the Common? Yes/No/Unsure answer in the spreadsheet; runs last so a sheet error can never block the email

if __name__ == '__main__':
    main()
