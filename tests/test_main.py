import pytest
from ..utils.date import today
from ..data_prep import get_words
from ..emailer import emailer

def test_get_words():
    sample_word, sample_translation = get_words()
    assert sample_word is not None
    assert sample_translation is not None
    assert isinstance(sample_word, str)
    assert isinstance(sample_translation, str)
    # assert sample_word == "foo" # Break test on purpose to see what happens

def test_emailer():
    sample_word: str = "this is a test: word"
    sample_translation: str = "this is a test: translation"
    emailer(sample_word, sample_translation)

if __name__ == '__main__':
    pytest.main()

