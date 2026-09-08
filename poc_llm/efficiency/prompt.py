"""Bounded system-prompt composition for the listen-only Reasoner proposal."""

from __future__ import annotations

from dataclasses import dataclass


MAXIMUM_TRUSTED_SETTINGS_CODEPOINTS = 20


class PromptError(ValueError):
    pass


@dataclass(frozen=True)
class PromptComposition:
    core: str
    trusted_settings: str
    system_message: str
    core_codepoints: int
    settings_codepoints: int


def compose_system_prompt(core: str, trusted_settings: str) -> PromptComposition:
    """Append bounded trusted settings without putting envelope policy in the prompt."""

    if not isinstance(core, str) or not core.strip():
        raise PromptError("prompt core must be nonblank")
    if not isinstance(trusted_settings, str) or not trusted_settings.strip():
        raise PromptError("trusted settings must be nonblank")
    if len(trusted_settings) > MAXIMUM_TRUSTED_SETTINGS_CODEPOINTS:
        raise PromptError("trusted settings exceed 20 codepoints")
    if any(character in trusted_settings for character in "\r\n\x00"):
        raise PromptError("trusted settings contain a control separator")
    normalized_core = core.strip()
    normalized_settings = trusted_settings.strip()
    return PromptComposition(
        core=normalized_core,
        trusted_settings=normalized_settings,
        system_message=f"{normalized_core}{normalized_settings}",
        core_codepoints=len(normalized_core),
        settings_codepoints=len(normalized_settings),
    )
