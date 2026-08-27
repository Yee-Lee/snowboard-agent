"""Pure parsers used by M4a target resource/offline acceptance collectors."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


class MetricsError(ValueError):
    """A target kernel snapshot is absent or malformed."""


def network_isolated(net_dev: str, route: str) -> bool:
    interfaces = []
    for line in net_dev.splitlines()[2:]:
        if ":" in line:
            name = line.split(":", 1)[0].strip()
            if name and name != "lo":
                interfaces.append(name)
    default_routes = []
    for line in route.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 2 and fields[0] != "lo" and fields[1] == "00000000":
            default_routes.append(fields[0])
    return not interfaces and not default_routes


def system_used_mib(meminfo: str) -> float:
    values: dict[str, int] = {}
    for line in meminfo.splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        fields = raw.split()
        if fields:
            try:
                values[key] = int(fields[0])
            except ValueError as error:
                raise MetricsError("meminfo contains a non-integer value") from error
    if "MemTotal" not in values or "MemAvailable" not in values:
        raise MetricsError("meminfo lacks MemTotal or MemAvailable")
    used_kib = values["MemTotal"] - values["MemAvailable"]
    if used_kib < 0:
        raise MetricsError("MemAvailable exceeds MemTotal")
    return used_kib / 1024


def descendants(parents: Mapping[int, int], owner_pid: int) -> set[int]:
    result: set[int] = set()
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if pid not in result and (parent == owner_pid or parent in result):
                result.add(pid)
                changed = True
    return result


def privacy_hits(
    blobs: Iterable[tuple[str, bytes]], sentinels: Iterable[str | bytes],
) -> list[str]:
    values = tuple(value for value in sentinels if value)
    hits: list[str] = []
    for locator, blob in blobs:
        text = blob.decode("utf-8", errors="ignore")
        if any(
            value in blob if isinstance(value, bytes) else value in text
            for value in values
        ):
            hits.append(locator)
    return hits
