def get_feedback_prompt(language: str) -> str:
    """
    Generates the system prompt for Pass 2 (grammar / vocabulary feedback).
    Model must return ONLY the JSON object below — no markdown, no prose.
    """
    return f"""\
Analyze this student's spoken {language} message for real language mistakes 
(grammar, conjugation, agreement, wrong word, unnatural phrasing).

Ignore: filler words, false starts, casual/informal speech, regional word 
variants, and likely transcription glitches. This is spoken language — judge 
it like natural speech, not formal writing.

Return ONLY this JSON, no markdown fences, no extra text:
{{
  "has_errors": true,
  "corrected_text": "full message corrected, sounding natural when spoken",
  "mistakes": [
    {{
      "original": "wrong word/phrase",
      "error_type": "verb_conjugation | agreement | article | preposition | vocabulary | word_order | phrasing",
      "fix": "corrected word/phrase",
      "explanation": "under 8 words, terse, like a linter warning (e.g. 'always capitalize I')"
    }}
  ]
}}

If no errors, "mistakes" is [] and corrected_text is the original message.
Max 4 mistakes — prioritize the ones that most affect meaning.
"""