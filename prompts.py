from config import target_country, target_language, student_primary_language


# The three target-country checks. Each is sent as its own request, with no system prompt, so no persona can bias the answer.
def direct_prompt(word: str, translation: str) -> str:
    return f"""
Do people in {target_country} commonly say the word or phrase '{word}' to mean '{translation}'?
Respond only with JSON: {{"answer": "Yes, No, or Unsure", "reason": "one short sentence in {student_primary_language}"}}
""".strip()


def reverse_prompt(translation: str) -> str:
    return f"""
What {target_language} words or phrases do people in {target_country} commonly say to mean '{translation}'? List up to 8. Keep phrases whole.
Respond only with JSON: {{"words_or_phrases": ["..."]}}
""".strip()


def region_prompt(word: str, translation: str) -> str:
    return f"""
In which {target_language}-speaking countries do people commonly say the word or phrase '{word}' to mean '{translation}'?
Respond only with JSON: {{"countries": ["country names in English"]}}
""".strip()


def generative_system_prompt() -> str:
    return f"""
You are a {target_language} teacher born and raised in {target_country}.
You help language students learn {target_language} through practical examples.
Always respond with valid JSON only — no extra text, no markdown.
""".strip()


def generative_user_prompt(
    word: str,
    sample_sentence_subject: str | None,
    sample_verb_tense: str,
    target_focus: str,
    apply_focus: bool,
    use_passive_se: bool,
) -> str:
    focus_instruction = f"Write the sample sentence to demonstrate: {target_focus}. " if apply_focus else ""

    if use_passive_se:
        task3_instruction = (
            f"Write the sentence as a passive se construction (e.g., 'se + verb + noun'). "
            f"Do not use a personal pronoun as the subject. "
            f"The sentence must use the {sample_verb_tense} tense."
        )
    else:
        task3_instruction = (
            f"The subject must be: '{sample_sentence_subject}'. "
            f"The sentence must use the {sample_verb_tense} tense. "
            f"{focus_instruction}"
        )

    return f"""
The language student is learning the {target_language} word or phrase: '{word}'.

Complete all three tasks below. Respond ONLY with a JSON object matching this exact schema:
{{"translation": "...", "synonyms": "...", "sample_sentence": "..."}}

Task 1 (translation): Provide the {student_primary_language} meaning of '{word}' as used in {target_country}. One short phrase only.

Task 2 (synonyms): List synonyms for '{word}' commonly used in {target_country}, ranked most-to-least common. Comma-separated list only.

Task 3 (sample_sentence): Write one example sentence using '{word}' in {target_language} as used in normal conversation in {target_country}.
{task3_instruction}
Do NOT explain your reasoning. Do NOT include any text outside the JSON object.
""".strip()
