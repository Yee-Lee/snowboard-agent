"""M4B-MEM-001: real policy and Linux sampler with synthetic integer counters."""
from dataclasses import replace

import pytest

from sbd.cognition.litert_lm.resource import (MemoryDecision, ProcessResource,
    ProcLLMResourceSampler, ResourceSampleError, SystemResourceSample, memory_decision)


def sample(available=1000, stamp=1):
    return SystemResourceSample(stamp, tuple(ProcessResource(i + 1, owner, 100, 10, 20, .1, 1)
        for i, owner in enumerate(("core", "vad", "asr", "tts", "llm"))),
        2000, available, 0, 0, 55.0, 0)


@pytest.mark.parametrize("available,speak,generate,expected", [
    (1000, 500, 1000, MemoryDecision.GENERATE), (999, 500, 1000, MemoryDecision.NOTICE),
    (500, 500, 1000, MemoryDecision.NOTICE), (499, 500, 1000, MemoryDecision.SILENT),
    (500, 500, 500, MemoryDecision.GENERATE), (499, 500, 500, MemoryDecision.SILENT),
], ids=["M01-G", "M01-Gminus1", "M01-S", "M01-Sminus1", "M01-equal", "M01-equal-below"])
def test_memory_decision_exact_boundaries(available, speak, generate, expected, record_property):
    record_property("test_id", "M4B-MEM-001")
    record_property("case_id", "M01")
    assert memory_decision(sample(available), min_mem_available_speak_bytes=speak,
                           min_mem_available_generate_bytes=generate) is expected


@pytest.mark.parametrize("changes", [
    {"mem_available_bytes": 2001}, {"oom_kill": 1},
    {"throttled_bits": 1}, {"temperature_c": float("nan")}, {"temperature_c": 80},
    {"temperature_c": -1}, {"mem_total_bytes": 1},
    {"processes": sample().processes + sample().processes[:1]},
    {"processes": sample().processes[:-1]},
    {"processes": (replace(sample().processes[0], start_time_ticks=101), *sample().processes[1:])},
    {"processes": (replace(sample().processes[0], pid=999), *sample().processes[1:])},
], ids=[f"M02-{i}" for i in range(11)])
def test_unhealthy_or_inconsistent_samples_fail_before_decision(changes):
    with pytest.raises(ResourceSampleError, match="^M4B_RESOURCE_INVALID$"):
        memory_decision(replace(sample(stamp=2), **changes), previous=sample(),
            min_mem_available_speak_bytes=500, min_mem_available_generate_bytes=1000)


@pytest.mark.parametrize("swap_used_bytes", [0, 1, 18 * 1024**2])
def test_M02_swap_growth_is_measured_not_a_health_stop(swap_used_bytes):
    current = replace(sample(stamp=2), swap_used_bytes=swap_used_bytes)
    assert memory_decision(current, previous=sample(),
        min_mem_available_speak_bytes=500,
        min_mem_available_generate_bytes=1000) is MemoryDecision.GENERATE
    assert current.swap_used_bytes == swap_used_bytes


@pytest.mark.parametrize("speak,generate", [(None, None), (0, 1), (2, 1), (True, 1), (1, float("inf"))],
                         ids=[f"M03-{i}" for i in range(5)])
def test_thresholds_have_no_source_default(speak, generate):
    with pytest.raises(ResourceSampleError):
        memory_decision(sample(), min_mem_available_speak_bytes=speak,
                        min_mem_available_generate_bytes=generate)


def _proc(tmp_path, pid, group=77):
    root = tmp_path / str(pid)
    root.mkdir()
    tail = ["S"] + ["0"] * 19
    tail[2], tail[11], tail[12], tail[17], tail[19] = str(group), "10", "5", "2", "100"
    (root / "stat").write_text(f"{pid} (private command) " + " ".join(tail))
    (root / "smaps_rollup").write_text("Pss: 10 kB\nRss: 20 kB\n")


def test_proc_sampler_counts_shared_vad_asr_once_and_detects_identity_loss(tmp_path):
    owners = {"core": [1], "vad": [2], "asr": [2], "tts": [3], "llm": [4]}
    for pid in range(1, 5):
        _proc(tmp_path, pid, group=77 if pid == 4 else pid)
    (tmp_path / "meminfo").write_text("MemTotal: 2048 kB\nMemAvailable: 1024 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB\n")
    (tmp_path / "vmstat").write_text("oom_kill 0\n")
    ticks = iter(range(1, 5))
    sampler = ProcLLMResourceSampler(tmp_path, ownership_registry=lambda: owners,
        temperature=lambda: 50., throttled=lambda: 0, clock=lambda: next(ticks), clock_ticks=100)
    result = sampler.sample(child_pid=4, child_pgid=77)
    assert len(result.processes) == 4 and result.combined_pss_bytes == 40 * 1024
    assert result.owner_pss_bytes("vad") == result.owner_pss_bytes("asr") == 10 * 1024
    _proc(tmp_path, 5, group=77)
    with pytest.raises(ResourceSampleError):
        sampler.sample(child_pid=4, child_pgid=77)
    (tmp_path / "4/stat").unlink()
    with pytest.raises(ResourceSampleError) as error:
        sampler.sample(child_pid=4, child_pgid=77)
    assert "private" not in str(error.value) and error.value.__suppress_context__


def test_proc_sampler_never_invents_missing_ownership_or_thermal_sources(tmp_path):
    with pytest.raises(ResourceSampleError):
        ProcLLMResourceSampler(tmp_path).sample(child_pid=1, child_pgid=1)


def test_proc_sampler_reads_pss_and_rss_from_one_snapshot(tmp_path, monkeypatch):
    owners = {"core": [1], "vad": [2], "asr": [2], "tts": [3], "llm": [4]}
    for pid in range(1, 5):
        _proc(tmp_path, pid, group=77 if pid == 4 else pid)
    (tmp_path / "meminfo").write_text("MemTotal: 2048 kB\nMemAvailable: 1024 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB\n")
    (tmp_path / "vmstat").write_text("oom_kill 0\n")
    sampler = ProcLLMResourceSampler(tmp_path, ownership_registry=lambda: owners,
        temperature=lambda: 50., throttled=lambda: 0, clock_ticks=100)
    read = sampler._read
    reads = []
    def changing_snapshot(path):
        if path == tmp_path / "4/smaps_rollup":
            reads.append(path)
            return "Pss: 100 kB\nRss: 110 kB\n" if len(reads) == 1 else "Pss: 10 kB\nRss: 20 kB\n"
        return read(path)
    monkeypatch.setattr(sampler, "_read", changing_snapshot)
    result = sampler.sample(child_pid=4, child_pgid=77)
    assert len(reads) == 1
    llm = next(p for p in result.processes if "llm" in p.owners)
    assert (llm.pss_bytes, llm.rss_bytes) == (102400, 112640)


def test_invalid_sample_preserves_values_and_reason_for_private_diagnostics():
    sampler = ProcLLMResourceSampler()
    before = sample()
    invalid = replace(sample(stamp=2), processes=(
        replace(before.processes[0], pss_bytes=200, rss_bytes=100), *before.processes[1:]))
    with pytest.raises(ResourceSampleError) as caught:
        sampler.validate_sample(invalid, before)
    assert caught.value.sample is invalid
    assert caught.value.previous is before
    assert caught.value.reason.startswith("pss_exceeds_rss_pid_")
    assert str(caught.value) == "M4B_RESOURCE_INVALID"


@pytest.mark.parametrize("corruption", [None, "time", "core"])
def test_M02_audio_rebase_preserves_health_and_non_audio_identity(corruption):
    previous = sample()
    audio = replace(previous.processes[2], pid=33, start_time_ticks=200)
    current = replace(sample(stamp=2), processes=(*previous.processes[:2], audio,
                                                 *previous.processes[3:]))
    class Registry:
        def rebase_previous(self, old, new):
            adjusted = replace(old, processes=new.processes)
            if corruption == "time":
                return replace(adjusted, monotonic_ns=0)
            if corruption == "core":
                return replace(adjusted, processes=(replace(adjusted.processes[0], pid=88),
                                                     *adjusted.processes[1:]))
            return adjusted
    sampler = ProcLLMResourceSampler(ownership_registry=Registry())
    if corruption:
        with pytest.raises(ResourceSampleError):
            sampler.validate_sample(current, previous)
    else:
        sampler.validate_sample(current, previous)
        sampler.validate_sample(current, previous)
        sampler.validate_sample(replace(current, swap_used_bytes=1), previous)
