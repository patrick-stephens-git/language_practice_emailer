from config import target_country, target_language, student_primary_language


def factual_system_prompt() -> str:
    return f"""
You are an expert {target_language} teacher and a native speaker from {target_country}.
Answer questions about vocabulary usage concisely and accurately.
Always respond with valid JSON only — no extra text, no markdown.
""".strip()


def factual_user_prompt(word: str) -> str:
    return f"""
The student is learning the {target_language} word or phrase: '{word}'.

Is '{word}' commonly used in {target_country}?
Answer "Yes" only if a native {target_country} speaker would naturally say this word or phrase themselves in normal everyday speech.
Any register counts: slang, colloquial, standard, or formal words that people still say out loud.
Merely being understood is NOT enough.
Answer "No" if native {target_country} speakers would normally choose a different word or phrase for the same meaning, if the word is mainly associated with other regions (for example Spain), if it is rare or archaic, or if it is understood there but not something people naturally say.

Respond ONLY with a JSON object matching this exact schema, with the keys in this order:
{{"reason": "...", "is_common": "..."}}

"reason": one or two short sentences written in {student_primary_language}, weighing whether {target_country} speakers use this word themselves or associate it with another region. If you answer "No" because a different word is more typical, name that word.
"is_common": exactly "Yes" or "No", consistent with your reason.

Do NOT include any text outside the JSON object.
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
