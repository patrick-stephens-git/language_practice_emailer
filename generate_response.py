from config import openai_api_key, target_country, target_focus_list, focus_weight, passive_se_weight, subject_list, subject_usted_list, verb_tense_list
from utils.logging_config import setup_logging
from prompts import direct_prompt, reverse_prompt, region_prompt, generative_system_prompt, generative_user_prompt
import openai
import json
import logging
import random
import unicodedata

logger = logging.getLogger(__name__)


def get_target_focus() -> str:
    return random.choice(target_focus_list)


def get_verb_tense() -> str:
    return random.choice(verb_tense_list)


def get_sample_sentence_subject() -> str:
    sample_sentence_subject: str = random.choice(subject_list)
    if sample_sentence_subject == 'usted':
        usted_subject: str = random.choice(subject_usted_list)
        sample_sentence_subject = f"{sample_sentence_subject} (who is a {usted_subject})"
    return sample_sentence_subject


def normalize(text: str) -> str:
    """Ignore capitals, punctuation and extra spaces, but keep accents."""
    text = unicodedata.normalize("NFC", text).casefold() # NFC makes composed and decomposed accents compare equal
    text = "".join(ch for ch in text if not unicodedata.category(ch).startswith("P"))
    return " ".join(text.split())


def match_list(items: list, target: str) -> str:
    """Yes if target is one whole item in the list, No if it isn't, Unsure if the list is empty."""
    if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
        raise ValueError(f"Expected a list of strings, got: {items!r}")
    if not items:
        return "Unsure"
    return "Yes" if normalize(target) in {normalize(item) for item in items} else "No"


def build_reason(direct_reason: str, countries: list[str]) -> str:
    """Return the Direct check's reason followed by a sentence naming the countries. Either part may be empty."""
    if direct_reason and not direct_reason.endswith((".", "!", "?")):
        direct_reason += "."
    if not countries:
        return direct_reason
    names: str = countries[0] if len(countries) == 1 else f"{', '.join(countries[:-1])} and {countries[-1]}"
    return f"{direct_reason} People in {names} commonly use this word.".strip()


def request_json(client: openai.OpenAI, prompt: str) -> dict:
    logger.info(f"Check prompt: {prompt}")
    response = client.chat.completions.create(
        model="gpt-6-luna", # efficient model for high-volume focused tasks; sufficient for structured factual JSON
        reasoning_effort="none", # skip reasoning so hidden reasoning tokens don't consume the small completion limit
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}, # enforced so json.loads never receives free-form text
        temperature=0, # factual questions have one best answer; randomness would only add error
        max_completion_tokens=300, # Room for the country and word lists so they are not cut off
    )
    raw: str = response.choices[0].message.content
    logger.info(f"Check raw response: {raw}")
    return json.loads(raw)


def check_common(client: openai.OpenAI, word: str, translation: str) -> tuple[str, str]:
    """Run the Direct, Reverse and Region checks. Returns (Yes / No / Unsure, reason)."""
    if not translation.strip(): # every prompt needs the meaning
        logger.error(f"No spreadsheet translation for '{word}'; checks skipped.")
        return "Unsure", ""

    # (name, prompt, function that turns the parsed JSON into Yes / No / Unsure)
    checks = (
        ("Direct", direct_prompt(word, translation), lambda data: str(data["answer"]).strip().rstrip(".").capitalize()), # any other answer ends up as Unsure below
        ("Reverse", reverse_prompt(translation), lambda data: match_list(data["words_or_phrases"], word)),
        ("Region", region_prompt(word, translation), lambda data: match_list(data["countries"], target_country)),
    )

    results: list[str] = []
    direct_reason: str = ""
    countries: list[str] = []
    for name, prompt, evaluate in checks:
        try: # each check fails on its own so the others still run and the email is never blocked
            data: dict = request_json(client, prompt)
            result: str = evaluate(data)
            if name == "Direct":
                direct_reason = str(data.get("reason") or "").strip()
            elif name == "Region":
                countries = data["countries"] # already validated by match_list
        except Exception as e:
            logger.exception(f"{name} check failed: {e}")
            result = "Failed"
        logger.info(f"{name} check result: {result}")
        results.append(result)

    verdict: str = results[0] if len(set(results)) == 1 and results[0] in ("Yes", "No") else "Unsure"
    logger.info(f"Common check verdict: {verdict}")
    return verdict, build_reason(direct_reason, countries)


def response_generation(word: str, translation: str) -> tuple[str, str, str, str, str]:
    use_passive_se: bool = random.random() < passive_se_weight
    sample_sentence_subject: str | None = None if use_passive_se else get_sample_sentence_subject()
    sample_verb_tense: str = get_verb_tense() # sampled before the generative call

    client = openai.OpenAI(api_key=openai_api_key, max_retries=2, timeout=30) # one client reused for all calls; retries and timeout guard against transient API errors

    ###############################################
    # Common-in-target-country checks: Direct, Reverse and Region, one request each (deterministic)
    ###############################################
    is_common, is_common_reason = check_common(client, word, translation)

    ###############################################
    # Generative request: translation, synonyms, sample_sentence
    ###############################################
    target_focus: str = get_target_focus()
    apply_focus: bool = (not use_passive_se) and (random.random() < focus_weight) # passive se and focus are mutually exclusive; applying focus requires a subject
    generative_system: str = generative_system_prompt()
    generative_user: str = generative_user_prompt(
        word=word,
        sample_sentence_subject=sample_sentence_subject,
        sample_verb_tense=sample_verb_tense,
        target_focus=target_focus,
        apply_focus=apply_focus,
        use_passive_se=use_passive_se,
    )
    logger.info(f"Sentence settings: passive se={use_passive_se}, subject={sample_sentence_subject}, verb tense={sample_verb_tense}, focus={target_focus if apply_focus else None}")
    logger.info(f"Generative user prompt: {generative_user}")

    ai_translation: str = "[unavailable]"
    example_synonyms: str = "[unavailable]"
    example_sentence: str = "[unavailable]"
    try:
        generative_response = client.chat.completions.create(
            model="gpt-6-luna", # efficient model for high-volume focused tasks; sufficient for structured factual JSON
            reasoning_effort="none", # skip reasoning so hidden reasoning tokens don't consume the small completion limit
            messages=[
                {"role": "system", "content": generative_system},
                {"role": "user", "content": generative_user},
            ],
            response_format={"type": "json_object"}, # enforced so json.loads never receives free-form text
            temperature=1.2, # 0.0–2.0; higher value adds variety to responses
            max_completion_tokens=160, # Sufficient for three fields including a full example sentence
        )
        generative_raw: str = generative_response.choices[0].message.content
        logger.info(f"Generative raw response: {generative_raw}")
        generative_data: dict = json.loads(generative_raw)
        ai_translation = str(generative_data.get("translation", "[unavailable]")).strip()
        example_synonyms = str(generative_data.get("synonyms", "[unavailable]")).strip()
        example_sentence = str(generative_data.get("sample_sentence", "[unavailable]")).strip()
        logger.info(f"AI translation: {ai_translation}")
        logger.info(f"AI synonyms: {example_synonyms}")
        logger.info(f"AI sample sentence: {example_sentence}")
    except json.JSONDecodeError as e:
        logger.exception(f"Generative JSON parse error: {e}")

    return ai_translation, example_synonyms, example_sentence, is_common, is_common_reason # order must match the tuple signature expected by main.py

if __name__ == '__main__':
    setup_logging()
    # word: str = "coger"
    # word: str = "ordenador"
    # word: str = "patata"
    # word: str = "joder"
    # word: str = "choclo"
    # word: str = "pileta"
    # word: str = "recoger"
    # word: str = "sudor"
    # word: str = "cima"
    # word: str = "acechar"
    # word: str = "embargar"
    # word: str = "verga" 
    # word: str = "no mames"
    # word: str = "neta"
    # word: str = "chido"
    # word: str = "a menos que"
    # word: str = "al paracer"
    # word: str = "en cuanto"
    # word: str = "por cierto"
    # word: str = "así como"
    # word: str = "a más tardar"
    word: str = "daltónico"
    translation: str = "colorblind" # meaning of the active word above; change it along with the word
    # word: str = "tajar"
    # word: str = "asdfsafsd"
    # word: str = "xxx"
    # word: str = "asolar"
    # word: str = "onza"
    # word: str = "en pos"
    # word = "qué anda"
    ai_translation, example_synonyms, example_sentence, is_common, is_common_reason = response_generation(word, translation)
    print(ai_translation)
    print(example_synonyms)
    print(example_sentence)
    print(is_common)
    print(is_common_reason)
