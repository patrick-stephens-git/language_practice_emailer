import logging
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

NO_NEW_SYNONYMS_MESSAGE: str = "All synonyms for this word are already in your word list."


def filter_known_synonyms(synonyms: str, known_words: list[str]) -> str:
    if synonyms.strip() == "[unavailable]": # LLM call failed upstream; nothing to filter
        return synonyms

    known_words_normalized: set[str] = {str(w).strip().lower() for w in known_words if str(w).strip()}

    candidate_synonyms: list[str] = [s.strip().rstrip(".").strip() for s in synonyms.split(",")]
    candidate_synonyms = [s for s in candidate_synonyms if s]

    new_synonyms: list[str] = [s for s in candidate_synonyms if s.lower() not in known_words_normalized]

    removed: list[str] = [s for s in candidate_synonyms if s not in new_synonyms]
    if removed:
        logger.info(f"Removed {len(removed)} synonym(s) already present in the spreadsheet word list: {', '.join(removed)}")
    logger.info(f"Synonyms after filtering: {', '.join(new_synonyms) or '(none left)'}")

    if not new_synonyms:
        return NO_NEW_SYNONYMS_MESSAGE

    return ", ".join(new_synonyms)


if __name__ == '__main__':
    setup_logging()
    example_synonyms: str = "instruir, educar, mostrar, enseñar."
    example_known_words: list[str] = ["enseñar", "aprender"]
    print(filter_known_synonyms(example_synonyms, example_known_words))
    print(filter_known_synonyms("instruir.", ["instruir"]))
