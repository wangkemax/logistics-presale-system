"""Bilingual document generation service.

Translates Chinese tender content to English (or vice versa)
for international clients. Uses LLM for high-quality translation.
"""

import json
import structlog
from app.core.llm import get_llm_client

logger = structlog.get_logger()


async def translate_content(
    content: str,
    source_lang: str = "zh",
    target_lang: str = "en",
    content_type: str = "tender",
) -> str:
    """Translate content between Chinese and English.

    Args:
        content: Source text.
        source_lang: Source language code (zh/en).
        target_lang: Target language code (zh/en).
        content_type: Context hint (tender/email/report).

    Returns:
        Translated text.
    """
    llm = get_llm_client()

    lang_names = {"zh": "Chinese (Simplified)", "en": "English"}
    context_hints = {
        "tender": "This is a logistics tender/proposal document. Use formal business language and industry-specific terminology.",
        "email": "This is a business email. Keep the tone professional but friendly.",
        "report": "This is a technical report. Maintain precision and clarity.",
    }

    system = f"""You are a professional translator specializing in logistics and supply chain.
Translate from {lang_names.get(source_lang, source_lang)} to {lang_names.get(target_lang, target_lang)}.

{context_hints.get(content_type, '')}

Rules:
1. Maintain the original structure and formatting
2. Use industry-standard terminology
3. Keep numbers, dates, and proper nouns unchanged
4. Preserve markdown formatting if present
5. Do NOT add any explanations — output only the translation"""

    result = await llm.generate(
        system_prompt=system,
        user_message=content,
        max_tokens=min(len(content) * 3, 8000),
        temperature=0.2,
    )

    return result.strip()


async def generate_bilingual_chapters(
    chapters: list[dict],
    source_lang: str = "zh",
) -> list[dict]:
    """Generate bilingual versions of tender chapters.

    Args:
        chapters: List of chapter dicts with 'title' and 'content'.
        source_lang: Language of the source chapters.

    Returns:
        Chapters with added translation fields.
    """
    target_lang = "en" if source_lang == "zh" else "zh"
    bilingual = []

    for ch in chapters:
        translated_title = await translate_content(
            ch.get("title", ""), source_lang, target_lang, "tender"
        )
        translated_content = await translate_content(
            ch.get("content", ""), source_lang, target_lang, "tender"
        )

        bilingual.append({
            **ch,
            f"title_{target_lang}": translated_title,
            f"content_{target_lang}": translated_content,
        })

        logger.info("chapter_translated", chapter=ch.get("chapter"), target=target_lang)

    return bilingual
