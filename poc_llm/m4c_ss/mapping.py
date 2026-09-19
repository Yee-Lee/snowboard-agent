"""The two frozen private fragment-to-TTS mappings for M4C-SS."""

from __future__ import annotations

from dataclasses import dataclass

from poc_llm.m4c_ss.controller import FragmentChannel, FragmentChannelError


B1 = "B1-IMMEDIATE-SEQUENTIAL"
B2 = "B2-ONE-LOOKAHEAD-COALESCE"
CANDIDATES = (B1, B2)


@dataclass(frozen=True, slots=True)
class MappingBatch:
    candidate: str
    sequences: tuple[int, ...]
    text: str
    coalesced: bool


async def next_mapping_batch(
    channel: FragmentChannel,
    candidate: str,
) -> MappingBatch | None:
    """Return the next exact-text TTS request without waiting for future look-ahead."""

    if candidate not in CANDIDATES:
        raise FragmentChannelError("UNKNOWN_MAPPING")
    fragments = await channel.receive_group(coalesce_available=candidate == B2)
    if fragments is None:
        return None
    return MappingBatch(
        candidate=candidate,
        sequences=tuple(item.sequence for item in fragments),
        text="".join(item.text for item in fragments),
        coalesced=len(fragments) == 2,
    )


async def acknowledge_mapping_batch(
    channel: FragmentChannel,
    operation_id: str,
    batch: MappingBatch,
) -> None:
    await channel.acknowledge_group(operation_id, batch.sequences)


async def abort_mapping_batch(
    channel: FragmentChannel,
    operation_id: str,
    batch: MappingBatch,
) -> None:
    await channel.abort_inflight_group(operation_id, batch.sequences)
