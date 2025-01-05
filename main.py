from data_prep import get_words
from emailer import emailer
from logging_config import setup_logging

def main() -> None: 
    setup_logging()
    sample_word, sample_translation = get_words()
    emailer(sample_word, sample_translation)

if __name__ == '__main__':
    main()