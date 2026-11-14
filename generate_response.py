from config import openai_api_key, common_confidence_threshold, target_focus_list, focus_weight, passive_se_weight, subject_list, subject_usted_list, verb_tense_list
from utils.logging_config import setup_logging
from prompts import factual_system_prompt, factual_user_prompt, generative_system_prompt, generative_user_prompt
import openai
import json
import math
import random
import re


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


def common_from_logprobs(logprob_content) -> tuple[str, float | None]:
    """Turn the probability of the is_common value token into Yes / No / Unsure.

    The model is deterministic (temperature 0), so the token it chose is its top pick and its own probability is the confidence.
    Returns (label, p_yes). p_yes is None when it could not be computed, in which case the label is "Unsure".
    """
    text_so_far: str = ""
    for token_info in logprob_content or []:
        value: str = token_info.token.strip().strip('"').lower()
        if value in ("yes", "no") and re.search(r'"is_common"\s*:\s*"?$', text_so_far): # this token is the Yes/No value, not text inside the reason
            p_chosen: float = math.exp(token_info.logprob)
            p_yes: float = p_chosen if value == "yes" else 1.0 - p_chosen # the answer is binary, so P(Yes) is whatever the "No" pick left over
            if p_yes >= common_confidence_threshold:
                return "Yes", p_yes
            if p_yes <= 1 - common_confidence_threshold:
                return "No", p_yes
            return "Unsure", p_yes
        text_so_far += token_info.token

    return "Unsure", None


def response_generation(word: str) -> tuple[str, str, str, str, str]:
    logger = setup_logging()

    use_passive_se: bool = random.random() < passive_se_weight
    sample_sentence_subject: str | None = None if use_passive_se else get_sample_sentence_subject()
    sample_verb_tense: str = get_verb_tense() # sampled before the generative call

    client = openai.OpenAI(api_key=openai_api_key, max_retries=2, timeout=30) # one client reused for both calls; retries and timeout guard against transient API errors

    ###############################################
    # Call 1 — Factual Query: is_common (deterministic; confidence read from token logprobs)
    ###############################################
    factual_system: str = factual_system_prompt()
    factual_user: str = factual_user_prompt(word)
    logger.info(f"Call 1 (factual) user prompt: {factual_user}")

    is_common: str = "Unsure"
    is_common_reason: str = "" # model's short explanation for the Yes/No; stays empty if the call or parse fails
    try:
        call1_response = client.chat.completions.create(
            model="gpt-6-luna", # efficient model for high-volume focused tasks; sufficient for structured factual JSON
            reasoning_effort="none", # skip reasoning so hidden reasoning tokens don't consume the small completion limit
            messages=[
                {"role": "system", "content": factual_system},
                {"role": "user", "content": factual_user},
            ],
            response_format={"type": "json_object"}, # enforced so the output is always the JSON shape the logprob parser expects
            temperature=0, # factual yes/no has one best answer; randomness would only add error
            logprobs=True, # return the probability behind each generated token; read for the is_common value
            max_completion_tokens=150, # Room for a one-to-two sentence reason plus the Yes/No value
        )
        call1_raw: str = call1_response.choices[0].message.content
        logger.info(f"Call 1 raw response: {call1_raw}")
        try:
            is_common_reason = str(json.loads(call1_raw).get("reason", "")).strip()
        except json.JSONDecodeError: # a bad reason must not discard the logprob-based answer below
            logger.error("Call 1 reason could not be parsed from the JSON response.")
        is_common, p_yes = common_from_logprobs(call1_response.choices[0].logprobs.content) # p_yes is only logged, to help tune common_confidence_threshold
        logger.info(f"Call 1 is_common={is_common} p_yes={p_yes}")
    except Exception as e: # any API or parsing failure degrades to Unsure rather than blocking the email
        logger.error(f"Call 1 failed: {e}")

    ###############################################
    # Call 2 — Generative Outputs: translation, synonyms, sample_sentence
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
    logger.info(f"Call 2 (generative) user prompt: {generative_user}")

    ai_translation: str = "[unavailable]"
    example_synonyms: str = "[unavailable]"
    example_sentence: str = "[unavailable]"
    try:
        call2_response = client.chat.completions.create(
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
        call2_raw: str = call2_response.choices[0].message.content
        logger.info(f"Call 2 raw response: {call2_raw}")
        call2_data: dict = json.loads(call2_raw)
        ai_translation = str(call2_data.get("translation", "[unavailable]")).strip()
        example_synonyms = str(call2_data.get("synonyms", "[unavailable]")).strip()
        example_sentence = str(call2_data.get("sample_sentence", "[unavailable]")).strip()
    except json.JSONDecodeError as e:
        logger.error(f"Call 2 JSON parse error: {e}")

    return ai_translation, example_synonyms, example_sentence, is_common, is_common_reason # order must match the tuple signature expected by main.py

if __name__ == '__main__':
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
    # word: str = "tajar"
    # word: str = "asdfsafsd"
    # word: str = "xxx"
    # word: str = "asolar"
    # word: str = "onza"
    # word: str = "en pos"
    # word = "qué anda"
    ai_translation, example_synonyms, example_sentence, is_common, is_common_reason = response_generation(word)
    print(ai_translation)
    print(example_synonyms)
    print(example_sentence)
    print(is_common)
    print(is_common_reason)
