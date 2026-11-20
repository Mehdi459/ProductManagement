"""Accès à Claude : génération de texte en streaming, réponses JSON, recherche web."""
from __future__ import annotations

import json
import re
from typing import Any, Callable

import anthropic

from . import config

FALLBACK_BETA = "server-side-fallback-2026-07-01"
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 12}

_client: anthropic.Anthropic | None = None


class GenerationError(RuntimeError):
    pass


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        # Lit ANTHROPIC_API_KEY (ou un profil `ant auth login`) automatiquement.
        _client = anthropic.Anthropic(max_retries=4)
    return _client


def _text_of(message) -> str:
    return "".join(b.text for b in message.content if b.type == "text")


def generate(
    prompt: str,
    system: str = "",
    max_tokens: int = 32000,
    web_search: bool = False,
    on_text: Callable[[str], None] | None = None,
    effort: str | None = None,
) -> str:
    """Appelle Claude en streaming et renvoie le texte final.

    - `fallbacks="default"` : si le modèle décline une requête, l'API la relance
      automatiquement sur un modèle de repli.
    - `web_search=True` : Claude peut chercher sur le web (tendances, best-sellers…).
    """
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    tools = [WEB_SEARCH_TOOL] if web_search else anthropic.omit
    collected = ""

    for _ in range(6):  # reprises éventuelles après `pause_turn` (recherche web longue)
        with client().beta.messages.stream(
            model=config.MODEL,
            max_tokens=max_tokens,
            system=system or anthropic.omit,
            messages=messages,
            tools=tools,
            thinking={"type": "adaptive"},
            output_config={"effort": effort or config.EFFORT},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        ) as stream:
            for event in stream:
                if (
                    on_text
                    and event.type == "content_block_delta"
                    and event.delta.type == "text_delta"
                ):
                    on_text(event.delta.text)
            final = stream.get_final_message()

        if final.stop_reason == "refusal":
            raise GenerationError("La demande a été refusée par le modèle. Reformulez le sujet.")
        if final.stop_reason == "pause_turn":
            collected += _text_of(final)
            messages = [messages[0], {"role": "assistant", "content": final.content}]
            continue
        collected += _text_of(final)
        if final.stop_reason == "max_tokens":
            collected += "\n"
        return collected.strip()
    return collected.strip()


_JSON_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> Any:
    """Récupère le premier objet/tableau JSON d'une réponse (avec ou sans bloc ```json)."""
    candidates = [m.group(1) for m in _JSON_RE.finditer(text)] + [text]
    for cand in candidates:
        cand = cand.strip()
        for opener, closer in (("{", "}"), ("[", "]")):
            start, end = cand.find(opener), cand.rfind(closer)
            if start != -1 and end > start:
                try:
                    return json.loads(cand[start : end + 1])
                except json.JSONDecodeError:
                    continue
    raise GenerationError("Réponse JSON illisible :\n" + text[:500])


def generate_json(prompt: str, system: str = "", web_search: bool = False, **kw) -> Any:
    instruction = (
        "\n\nRéponds UNIQUEMENT avec du JSON valide dans un bloc ```json ... ```, "
        "sans texte avant ni après."
    )
    last_error: Exception | None = None
    for _ in range(2):
        text = generate(prompt + instruction, system=system, web_search=web_search, **kw)
        try:
            return extract_json(text)
        except GenerationError as e:
            last_error = e
    raise last_error  # type: ignore[misc]
