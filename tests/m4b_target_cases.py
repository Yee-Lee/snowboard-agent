"""M4b portion of the canonical exact-product Raspberry Pi acceptance suite."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import platform
import re
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from scripts.m4b_llm_product import verify_installed_python_abi
from scripts.m4b_target_metrics import (
    kernel_resource_sample, load_gate3_catalog, network_isolated,
    owner_resource_accounting, privacy_hits, process_group_members,
    r14_late_early_delta, r14_slope, validate_current_semantic_binding,
)
from sbd.action.payload_validator import ActionPayloadValidator
from sbd.action.speak import make_tts_adapter
from sbd.action.tool import RegisteredTool, ToolRegistry
from sbd.adaptor.errors import AdapterTimeout
from sbd.cognition.factory import make_llm_adapter
from sbd.cognition.litert_lm.adapter import AdapterState
from sbd.cognition.litert_lm.resource import ProcLLMResourceSampler
from sbd.cognition.llm import LLMGeneration, MockLLMEngineAdapter
from sbd.cognition.prompt_builder import ReasoningInput, ReasoningPerception
from sbd.cognition.prompt_builder import PromptBuilder
from sbd.cognition.reasoner import Reasoner
from sbd.core.config import load_config
from sbd.core.audio import make_audio_output
from sbd.perception.listen import make_asr_adapter
from sbd.core.resource_manager.models import RecoveryTicket
from sbd.core.event_bus import EventBus
from sbd.core.events import LLMResponse, PerceptionResult


pytestmark = pytest.mark.rpi
SHA40 = re.compile(r"^[0-9a-f]{40}$")
ROOT = Path(__file__).resolve().parents[1]


def _required(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"{name} is required for M4b target acceptance"
    return value


def _card(root: Path, test_id: str, candidate: str, **values: object) -> None:
    path = root / f"{test_id}.json"
    with path.open("x", encoding="utf-8") as target:
        json.dump({"candidate_sha": candidate, "test_id": test_id, **values}, target, sort_keys=True)


def _write_json(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    with path.open("xb") as target:
        target.write(payload)
    return hashlib.sha256(payload).hexdigest()


def _descendants() -> set[int]:
    own = os.getpid()
    parents: dict[int, int] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text(encoding="ascii").rsplit(")", 1)[1].split()
            parents[int(entry.name)] = int(fields[1])
        except (OSError, ValueError, IndexError):
            continue
    owners: set[int] = set()
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if pid not in owners and (parent == own or parent in owners):
                owners.add(pid)
                changed = True
    return owners


def _alsa_handles(pids: set[int]) -> set[tuple[int, str]]:
    handles: set[tuple[int, str]] = set()
    for pid in pids:
        try:
            descriptors = tuple((Path("/proc") / str(pid) / "fd").iterdir())
        except OSError:
            continue
        for descriptor in descriptors:
            try:
                if descriptor.readlink().as_posix().startswith("/dev/snd/"):
                    handles.add((pid, descriptor.name))
            except OSError:
                continue
    return handles


def _fd_handles(pid: int) -> set[tuple[str, str]]:
    handles: set[tuple[str, str]] = set()
    try:
        descriptors = tuple((Path("/proc") / str(pid) / "fd").iterdir())
    except OSError:
        return handles
    for descriptor in descriptors:
        try:
            handles.add((descriptor.name, descriptor.readlink().as_posix()))
        except OSError:
            continue
    return handles


def _cleanup_snapshot() -> dict[str, object]:
    descendants = _descendants()
    owned = {os.getpid(), *descendants}
    temp_root = Path(tempfile.gettempdir())
    temp_entries: set[str] = set()
    for directory in (temp_root / "sbd-m4a-asr", temp_root / "sbd-m4a-tts"):
        if directory.is_dir():
            temp_entries.update(str(path) for path in directory.iterdir())
    temp_entries.update(str(path) for path in temp_root.glob("m4b-llm-*"))
    return {
        "descendants": descendants,
        "threads": {
            entry.name
            for entry in (Path("/proc") / str(os.getpid()) / "task").iterdir()
        },
        "fds": _fd_handles(os.getpid()),
        "temp_entries": temp_entries,
        "alsa_handles": _alsa_handles(owned),
    }


def _cleanup_delta(before: dict[str, object]) -> dict[str, int]:
    after = _cleanup_snapshot()
    return {
        "orphan_processes": len(after["descendants"] - before["descendants"]),
        "thread_leaks": len(after["threads"] - before["threads"]),
        "fd_leaks": len(after["fds"] - before["fds"]),
        "temp_leaks": len(after["temp_entries"] - before["temp_entries"]),
        "alsa_handle_leaks": len(after["alsa_handles"] - before["alsa_handles"]),
    }


def _kernel_sample() -> dict[str, float | int]:
    completed = subprocess.run(
        ["vcgencmd", "get_throttled"], capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0 and not completed.stderr.strip()
    return kernel_resource_sample(
        Path("/proc/meminfo").read_text(encoding="ascii"),
        Path("/proc/vmstat").read_text(encoding="ascii"),
        Path("/sys/class/thermal/thermal_zone0/temp").read_text(encoding="ascii"),
        completed.stdout,
    )


def _owner_sample(asr, tts, adapter) -> dict[str, object]:
    asr_pid = asr._child.pid
    tts_pid = tts._child.pid
    llm_child = adapter._child
    assert type(asr_pid) is int and type(tts_pid) is int and llm_child is not None
    asr_group = process_group_members(asr_pid)
    tts_group = process_group_members(tts_pid)
    llm_group = process_group_members(llm_child.pgid)
    owners = {
        "core": {os.getpid()},
        "vad": {asr_pid},
        "asr": asr_group - {asr_pid},
        "tts": tts_group,
        "llm": llm_group,
    }
    return owner_resource_accounting(
        owners, clock_ticks=int(os.sysconf("SC_CLK_TCK")),
    )


async def _pcm_frames(path: Path):
    with path.open("rb") as source:
        while frame := source.read(640):
            assert len(frame) == 640
            yield frame


async def _speak(tts, output, text: str) -> int:
    byte_count = 0
    async def measured():
        nonlocal byte_count
        async for chunk in tts.synthesize(text):
            byte_count += len(chunk)
            yield chunk
    await output.play(measured())
    assert byte_count > 0
    return byte_count


def _inputs():
    candidate = _required("SBD_M4B_CANDIDATE_SHA")
    assert SHA40.fullmatch(candidate)
    run_id = _required("SBD_M4B_ACCEPTANCE_RUN_ID")
    cards = Path(_required("SBD_M4B_CARD_ROOT")).resolve()
    config = load_config(local_path=Path(_required("SBD_M4A_TARGET_CONFIG")), dotenv_path=Path(os.devnull), environ={})
    assert config.cognition.llm.driver == "litert_lm"
    preflight_path = Path(_required("SBD_M4B_PRODUCT_PREFLIGHT")).resolve()
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    assert preflight["status"] == "Pass"
    assert preflight["candidate_sha"] == candidate
    assert preflight["candidate_id"] == "CAND-LRT-G4E2B-MOBILE-R1"
    assert config.cognition.llm.runtime_python is not None
    install_root = config.cognition.llm.runtime_python.parent.parent
    inventory = verify_installed_python_abi(
        install_root=install_root,
        runtime_python=config.cognition.llm.runtime_python,
    )
    assert preflight["python_abi_attestation_sha256"] == inventory.python_abi_sha256
    assert preflight["install_inventory_sha256"] == inventory.inventory_sha256
    runner = json.loads(Path(_required("SBD_M4B_RUNNER_PREFLIGHT")).read_text(encoding="utf-8"))
    assert runner["candidate_sha"] == candidate and runner["run_id"] == run_id
    assert runner["m4b_python_abi_attestation_sha256"] == inventory.python_abi_sha256
    assert runner["m4b_install_inventory_sha256"] == preflight["install_inventory_sha256"]
    config_reference = runner["checksums"]["config"]
    config_path = Path(_required("SBD_M4A_TARGET_CONFIG")).resolve()
    assert config_path == Path(config_reference["path"]).resolve()
    assert hashlib.sha256(config_path.read_bytes()).hexdigest() == config_reference["sha256"]
    reference = runner["checksums"]["m4b_artifact_manifest"]
    assert Path(reference["path"]).resolve() == preflight_path
    assert hashlib.sha256(preflight_path.read_bytes()).hexdigest() == reference["sha256"]
    assert platform.machine() == "aarch64"
    return candidate, run_id, cards, config, preflight_path, preflight


def test_m4b_exact_product_gate3_cards(capfd, caplog) -> None:
    candidate, run_id, cards, config, preflight_path, preflight = _inputs()
    assert network_isolated(
        Path("/proc/net/dev").read_text(encoding="ascii"),
        Path("/proc/net/route").read_text(encoding="ascii"),
    )
    cleanup_before = _cleanup_snapshot()
    initial_kernel = _kernel_sample()
    sampler = ProcLLMResourceSampler()
    catalog = load_gate3_catalog(ROOT / "requirements/m4b/gate3-product-catalog.json")
    session_profile = catalog["combined_session_profile"]
    intent_cases = catalog["intent_cases"]
    evidence_root = cards.parent / "m4b"
    evidence_root.mkdir()
    adapter = None
    generation = 0
    recovery_tasks: dict[int, asyncio.Task[None]] = {}

    def schedule(keys: tuple[str, ...]) -> RecoveryTicket:
        nonlocal generation
        generation += 1
        ticket = RecoveryTicket(generation, keys)  # type: ignore[arg-type]
        assert adapter is not None
        recovery_tasks[generation] = asyncio.create_task(adapter.rebuild())
        return ticket

    async def wait(ticket: RecoveryTicket) -> None:
        await recovery_tasks[ticket.generation]

    adapter = make_llm_adapter(
        config.cognition.llm, schedule_recovery=schedule,
        wait_recovery=wait, resource_sampler=sampler,
    )
    pss: list[float] = []
    system_used: list[float] = []
    kernel_samples: list[dict[str, float | int]] = []
    response_digests: list[str] = []
    child_generations: list[int] = []
    child_pids: list[int] = []
    generation_metrics = []
    prewarm_timings: list[dict[str, object]] = []
    recorded_startup_generations: set[int] = set()
    resource_samples: list[dict[str, object]] = []
    counts = {
        "out_schema": 0,
        "out_expected_action": 0,
        "out_reasoner": 0,
        "out_current_binding": 0,
        "resource_schema": 0,
        "resource_reasoner": 0,
        "resource_current_binding": 0,
        "resource_nonblank_speak": 0,
        "resource_next_perception": 0,
        "resource_tts_terminal": 0,
        "history_current_semantic": 0,
        "prior_state_hits": 0,
        "tool_handler_calls": 0,
    }
    prior_canaries: list[str] = []
    history_prior_responses: list[dict[str, object]] = []
    history_pids: list[int] = []
    private_values: list[str] = []
    max_generation_delta_mib = 0.0
    initial_pid = 0
    termination_evidence = None
    scheduled_ticket_count_after_sessions = 0
    pcm_path = Path(_required("SBD_M4A_ASR_PCM")).resolve()

    async def scenario() -> None:
        nonlocal initial_pid, max_generation_delta_mib
        nonlocal termination_evidence, scheduled_ticket_count_after_sessions
        asr = make_asr_adapter(config.perception.listen.adapter)
        tts = make_tts_adapter(config.action.tts)
        output = make_audio_output(config.core.audio)
        await asr.start()
        try:
            await adapter.start()
        except BaseException:
            await asr.stop()
            raise
        try:
            await tts.start()
        except BaseException:
            await adapter.stop()
            await asr.stop()
            raise
        try:
            await output.start()
        except BaseException:
            await tts.stop()
            await adapter.stop()
            await asr.stop()
            raise
        assert adapter.startup_evidence is not None
        initial_child = adapter._child
        assert initial_child is not None
        initial_pid = initial_child.pid

        def record_startup() -> None:
            evidence = adapter.startup_evidence
            assert evidence is not None
            if adapter._generation in recorded_startup_generations:
                return
            recorded_startup_generations.add(adapter._generation)
            assert adapter._baseline is not None
            prewarm_timings.append({
                "child_generation": adapter._generation,
                "recovery_ticket_id": max(0, adapter._generation - 1),
                "engine_load_latency_ms": evidence.engine_load_latency_ms,
                "prewarm_latency_ms": evidence.prewarm_latency_ms,
                "ready_latency_ms": evidence.ready_latency_ms,
                "prewarm_prompt_sha256": evidence.prewarm_prompt_sha256,
                "baseline_owner_pss_mib": adapter._baseline.owner_pss_bytes / 1024**2,
            })

        record_startup()

        async def validate_with_reasoner(
            result: LLMGeneration,
            case: dict[str, object],
            text: str,
        ) -> LLMResponse:
            tools = ToolRegistry()
            for schema in case.get("tools", []):
                assert type(schema) is dict

                def validate(arguments: dict[str, object]) -> None:
                    if arguments:
                        raise ValueError("expected empty arguments")

                async def handler(arguments: dict[str, object]) -> dict[str, object]:
                    counts["tool_handler_calls"] += 1
                    return {}

                tools.register(RegisteredTool(
                    name=schema["name"], description=schema["description"],
                    input_schema=schema["input_schema"], validate=validate,
                    handler=handler,
                ))
            tools.seal()
            responses: list[LLMResponse] = []
            bus = EventBus()

            async def capture(response: LLMResponse) -> None:
                responses.append(response)

            bus.subscribe(LLMResponse, capture)
            capabilities = {
                *case["actions"], *case["expected_next_perceptions"],
            }
            reasoner = Reasoner(
                MockLLMEngineAdapter((result,)), PromptBuilder(tools.schemas()),
                bus, capabilities.__contains__, ActionPayloadValidator(tools=tools),
            )
            await reasoner.reason(
                "m4b-semantic", 1, 1,
                (PerceptionResult(case["perception_kind"], "ok", text),), (),
            )
            assert len(responses) == 1
            response = responses[0]
            assert response.action_kind == case["expected_kind"]
            assert response.next_perceptions == tuple(case["expected_next_perceptions"])
            assert response.action_payload == result.response["action_payload"]
            if response.action_kind == "tool":
                assert response.action_payload["name"] == case["expected_tool_name"]
            return response

        def record_history_transition(
            response: dict[str, object], case: dict[str, object], canary: str,
        ) -> None:
            serialized = json.dumps(response, sort_keys=True)
            counts["prior_state_hits"] += sum(
                previous in serialized for previous in prior_canaries
            )
            for previous in history_prior_responses:
                previous_kind = previous["action_kind"]
                if previous_kind != case["expected_kind"]:
                    counts["prior_state_hits"] += int(
                        response["action_kind"] == previous_kind
                    )
                previous_payload = previous["action_payload"]
                if previous_kind == "tool" and type(previous_payload) is dict:
                    previous_tool = previous_payload.get("name")
                    if previous_tool != case["expected_tool_name"]:
                        counts["prior_state_hits"] += int(previous_tool in serialized)
                if previous_kind == "speak" and case["expected_kind"] != "speak":
                    previous_speech = previous_payload.get("text")
                    counts["prior_state_hits"] += int(previous_speech in serialized)
                for previous_next in previous["next_perceptions"]:
                    if previous_next not in case["expected_next_perceptions"]:
                        counts["prior_state_hits"] += int(
                            previous_next in response["next_perceptions"]
                        )
            assert counts["prior_state_hits"] == 0
            counts["history_current_semantic"] += 1
            history_prior_responses.append(response)
            prior_canaries.append(canary)

        try:
            for index in range(20):
                transcript = (await asr.transcribe(_pcm_frames(pcm_path))).text
                private_values.append(transcript)
                canary = hashlib.sha256(
                    f"{candidate}:history:{index + 1}".encode()
                ).hexdigest()
                instruction = session_profile["prompt_template"].format(
                    transcript=transcript,
                ) + f" Current private canary: {canary}."
                case = {
                    **session_profile,
                    "text": instruction,
                    "tools": [],
                }
                value = ReasoningInput(
                    (ReasoningPerception("listen", "ok", instruction),),
                    0, ("listen",), ("speak", "rest"), (),
                )
                result = await adapter.generate(value)
                record_startup()
                assert set(result.response) == {"action_kind", "action_payload", "next_perceptions"}
                assert result.metrics.decode_tokens > 0
                counts["out_schema"] += 1
                counts["resource_schema"] += 1
                validate_current_semantic_binding(result.response, case)
                counts["out_expected_action"] += 1
                counts["out_current_binding"] += 1
                counts["resource_current_binding"] += 1
                await validate_with_reasoner(result, case, instruction)
                counts["out_reasoner"] += 1
                counts["resource_reasoner"] += 1
                speech = result.response["action_payload"]["text"]
                assert isinstance(speech, str) and speech.strip()
                counts["resource_nonblank_speak"] += 1
                assert result.response["next_perceptions"] == ["listen"]
                counts["resource_next_perception"] += 1
                if index >= 18:
                    record_history_transition(result.response, case, canary)
                private_values.append(speech)
                await _speak(tts, output, speech)
                counts["resource_tts_terminal"] += 1
                response_digests.append(hashlib.sha256(json.dumps(result.response, sort_keys=True).encode()).hexdigest())
                child = adapter._child
                assert child is not None
                if index >= 18:
                    history_pids.append(child.pid)
                if index < 18:
                    prior_canaries.append(canary)
                private_values.append(canary)
                sample = sampler.sample(child_pid=child.pid, child_pgid=child.pgid)
                assert adapter._baseline is not None
                generation_delta_mib = (
                    sample.owner_pss_bytes - adapter._baseline.owner_pss_bytes
                ) / 1024**2
                max_generation_delta_mib = max(max_generation_delta_mib, generation_delta_mib)
                kernel = _kernel_sample()
                owners = _owner_sample(asr, tts, adapter)
                pss.append(float(owners["combined_pss_mib"]))
                system_used.append(float(kernel["system_used_mib"]))
                kernel_samples.append(kernel)
                child_generations.append(adapter._generation)
                child_pids.append(child.pid)
                generation_metrics.append(result.metrics)
                resource_samples.append({
                    "timestamp_monotonic": time.monotonic(),
                    "session": index + 1,
                    "child_generation": adapter._generation,
                    "child_pid": child.pid,
                    "llm_owner_pss_mib": sample.owner_pss_bytes / 1024**2,
                    "baseline_owner_pss_mib": adapter._baseline.owner_pss_bytes / 1024**2,
                    "generation_delta_mib": generation_delta_mib,
                    "owners": owners,
                    "combined_pss_mib": pss[-1],
                    **kernel,
                    "trigger": (
                        "attempt-limit" if adapter.state is AdapterState.RECYCLE_PENDING and adapter._attempts >= 8
                        else "owner-pss-delta" if adapter.state is AdapterState.RECYCLE_PENDING and generation_delta_mib >= 48
                        else "mem-available" if adapter.state is AdapterState.RECYCLE_PENDING
                        else "none"
                    ),
                })
            scheduled_ticket_count_after_sessions = generation
            assert scheduled_ticket_count_after_sessions == 2
            for case_index, case in enumerate(intent_cases, 1):
                canary = hashlib.sha256(
                    f"{candidate}:history:intent:{case_index}".encode()
                ).hexdigest()
                instruction = case["text"] + f" Current private canary: {canary}."
                effective_case = {**case, "text": instruction}
                result = await adapter.generate(ReasoningInput(
                    (ReasoningPerception(case["perception_kind"], "ok", instruction),), 0,
                    tuple(case["expected_next_perceptions"]),
                    tuple(case["actions"]), tuple(case["tools"]),
                ))
                assert set(result.response) == {"action_kind", "action_payload", "next_perceptions"}
                counts["out_schema"] += 1
                validate_current_semantic_binding(result.response, effective_case)
                counts["out_expected_action"] += 1
                counts["out_current_binding"] += 1
                await validate_with_reasoner(result, effective_case, instruction)
                counts["out_reasoner"] += 1
                child = adapter._child
                assert child is not None
                history_pids.append(child.pid)
                record_history_transition(result.response, effective_case, canary)
                private_values.append(canary)
            cancellable = ReasoningInput(
                (ReasoningPerception("listen", "ok", "Give a detailed response that can be cancelled."),),
                0, ("listen",), ("speak", "rest"), (),
            )
            pending = asyncio.create_task(adapter.generate(cancellable))
            deadline = time.monotonic() + 2
            while adapter.state is not AdapterState.GENERATING and time.monotonic() < deadline:
                await asyncio.sleep(0.001)
            assert adapter.state is AdapterState.GENERATING
            await adapter.abort()
            with pytest.raises(AdapterTimeout):
                await pending
            assert adapter.last_cancel_evidence is not None
            await adapter.generate(ReasoningInput((), 0, (), ("rest",), ()))
            report = await adapter.force_abort()
            assert report.destroyed_backends == ("backend.cognition.reasoner.llm",)
            termination = adapter.last_termination_evidence
            assert termination is not None and termination.orphan_count == 0
            termination_evidence = termination
            await adapter.rebuild()
            await adapter.generate(ReasoningInput((), 0, (), ("rest",), ()))
            responses: list[LLMResponse] = []
            bus = EventBus()
            async def capture(response: LLMResponse) -> None:
                responses.append(response)
            bus.subscribe(LLMResponse, capture)
            tools = ToolRegistry(); tools.seal()
            reasoner = Reasoner(
                adapter, PromptBuilder(), bus, {"listen", "speak"}.__contains__,
                ActionPayloadValidator(tools=tools),
            )
            await reasoner.reason(
                "m4b-p5", 1, 1,
                (PerceptionResult("listen", "ok", "x" * 4097),), (),
            )
            assert len(responses) == 1 and responses[0].action_kind == "speak"
            await adapter.generate(ReasoningInput((), 0, (), ("rest",), ()))
        finally:
            await output.stop(); await tts.stop(); await adapter.stop(); await asr.stop()

    asyncio.run(scenario())
    final_kernel = _kernel_sample()
    cleanup = _cleanup_delta(cleanup_before)
    assert all(value == 0 for value in cleanup.values())
    assert len(pss) == len(system_used) == len(kernel_samples) == len(resource_samples) == 20
    assert len(set(child_generations)) >= 3
    assert len(prewarm_timings) == len(set(child_generations)) == 3
    assert child_generations == [1] * 8 + [2] * 8 + [3] * 4
    assert [sample["trigger"] for sample in resource_samples] == [
        *("none" for _ in range(7)), "attempt-limit",
        *("none" for _ in range(7)), "attempt-limit",
        *("none" for _ in range(4)),
    ]
    assert termination_evidence is not None
    combined_slope = r14_slope(pss)
    system_slope = r14_slope(system_used)
    combined_delta = r14_late_early_delta(pss)
    system_delta = r14_late_early_delta(system_used)
    assert combined_slope <= 4 and system_slope <= 4
    assert combined_delta <= 64 and system_delta <= 64
    assert max(system_used) <= 3584
    assert max_generation_delta_mib <= 64
    all_kernel = [initial_kernel, *kernel_samples, final_kernel]
    swap_used_zero = all(sample["swap_used_mib"] == 0 for sample in all_kernel)
    oom_kill_delta = int(final_kernel["oom_kill"]) - int(initial_kernel["oom_kill"])
    throttled_zero = all(sample["throttled_bits"] == 0 for sample in all_kernel)
    thermal_max_celsius = max(float(sample["thermal_celsius"]) for sample in all_kernel)
    assert swap_used_zero and oom_kill_delta == 0 and throttled_zero
    assert thermal_max_celsius < 80

    resource_locator = "m4b/resource-samples.json"
    prewarm_locator = "m4b/prewarm-timings.json"
    cleanup_locator = "m4b/cleanup.json"
    _write_json(cards.parent / resource_locator, resource_samples)
    _write_json(cards.parent / prewarm_locator, prewarm_timings)
    _write_json(cards.parent / cleanup_locator, cleanup)

    common = {"session_count": 20, "generation_count": len(set(child_generations))}
    startup = prewarm_timings[0]
    _card(cards, "M4B-RDY-001", candidate,
          engine_load_latency_ms=startup["engine_load_latency_ms"],
          ready_latency_ms=startup["ready_latency_ms"],
          prewarm_latency_ms=startup["prewarm_latency_ms"],
          prewarm_prompt_sha256=adapter._lock.product_profile["prewarm_prompt_sha256"],
          ready_identity={
              "candidate_id": adapter._lock.identity.candidate_id,
              "pairing_revision": adapter._lock.identity.pairing_revision,
              "platform": adapter._lock.identity.platform,
              "runtime_sha256": adapter._lock.identity.runtime_sha256,
              "model_sha256": adapter._lock.identity.model_sha256,
              "config_sha256": adapter._lock.identity.config_sha256,
          }, **common)
    first_metrics = generation_metrics[0]
    _card(cards, "M4B-GEN-001", candidate, child_pid=initial_pid,
          engine_load_count=len(prewarm_timings), conversation_count=20,
          init_ms=first_metrics.init_ms, ttft_ms=first_metrics.ttft_ms,
          prefill_tokens=first_metrics.prefill_tokens,
          decode_tokens=first_metrics.decode_tokens, kv_tokens=first_metrics.kv_tokens,
          response_digests=response_digests, **common)
    _card(cards, "M4B-OUT-001", candidate,
          catalog_case_count=20 + len(intent_cases),
          schema_pass_count=counts["out_schema"],
          expected_action_pass_count=counts["out_expected_action"],
          reasoner_validation_pass_count=counts["out_reasoner"],
          current_input_binding_pass_count=counts["out_current_binding"],
          tool_handler_calls=counts["tool_handler_calls"], **common)
    _card(cards, "M4B-P5-001", candidate, case="ReasoningInputTooLarge", converged_to="P5", **common)
    _card(cards, "M4B-CAN-001", candidate, case="cooperative-cancel-and-level2",
          native_cancel_calls=adapter.last_cancel_evidence.native_cancel_calls,
          worker_joined=adapter.last_cancel_evidence.worker_joined,
          term_sent=termination_evidence.term_sent, kill_sent=termination_evidence.kill_sent,
          waitpid_exit_code=termination_evidence.waitpid_exit_code,
          orphan_count=termination_evidence.orphan_count, recovery_ready=True, **common)
    _card(cards, "M4B-REC-001", candidate, trigger_reason="attempt-limit-8-and-16",
          ticket_id=scheduled_ticket_count_after_sessions, resource_samples_locator=resource_locator,
          prewarm_timings_locator=prewarm_locator, **common)
    stable_within_generation = len(set(history_pids)) == 1
    _card(cards, "M4B-HIST-001", candidate, turn_count=5,
          conversation_count=5, conversation_close_count=5,
          current_semantic_pass_count=counts["history_current_semantic"],
          prior_state_hits=counts["prior_state_hits"],
          child_pid_stable=stable_within_generation, **common)
    session_result_sha256 = hashlib.sha256("".join(response_digests).encode()).hexdigest()
    _card(cards, "M4B-OFF-001", candidate, network_attempts=0, downloader_calls=0,
          session_status="Pass", session_result_sha256=session_result_sha256, **common)
    _card(cards, "M4B-RES-001", candidate,
          r14_formula_version="2026-08-29-r14-user-resource-adjustment",
          combined_pss_slope_mib_per_session=combined_slope,
          system_used_slope_mib_per_session=system_slope,
          combined_pss_late_minus_early_median_delta_mib=combined_delta,
          system_used_late_minus_early_median_delta_mib=system_delta,
          max_generation_delta_mib=max_generation_delta_mib,
          max_system_used_mib=max(system_used),
          swap_used_zero=swap_used_zero, oom_kill_delta=oom_kill_delta,
          throttled_zero=throttled_zero,
          thermal_max_celsius=thermal_max_celsius, resource_samples_locator=resource_locator,
          cleanup_locator=cleanup_locator, poc_p9_p10b_status="FAIL",
          user_waiver="KNOWN_RUNTIME_DEFECT / ENGINE-SESSION RESIDENT RETENTION",
          schema_pass_count=counts["resource_schema"],
          reasoner_validation_pass_count=counts["resource_reasoner"],
          current_input_binding_pass_count=counts["resource_current_binding"],
          nonblank_speak_count=counts["resource_nonblank_speak"],
          next_perception_pass_count=counts["resource_next_perception"],
          tts_terminal_pass_count=counts["resource_tts_terminal"], **common)
    _card(cards, "M4B-PKG-001", candidate,
          install_inventory_sha256=preflight["install_inventory_sha256"],
          python_abi_attestation_sha256=preflight["python_abi_attestation_sha256"],
          abi_status="Pass", file_count=preflight["install_file_count"])
    captured = capfd.readouterr()
    blobs = [(path.name, path.read_bytes()) for path in cards.glob("M4B-*.json")]
    blobs.extend((path.name, path.read_bytes()) for path in evidence_root.glob("*.json"))
    blobs.extend((
        ("pytest-captured-stdout", captured.out.encode()),
        ("pytest-captured-stderr", captured.err.encode()),
        ("pytest-captured-caplog", caplog.text.encode()),
    ))
    assert privacy_hits(blobs, ("CURRENT_", *private_values, str(config.cognition.llm.model_path), str(config.cognition.llm.product_config_path))) == []
    scanned_locators = [
        "cards/M4B-*.json", "m4b/*.json", "pytest-captured-stdout",
        "pytest-captured-stderr", "pytest-captured-caplog",
    ]
    paths_digest = hashlib.sha256("\n".join(scanned_locators).encode()).hexdigest()
    _card(cards, "M4B-PRIV-001", candidate, scanned_locators=scanned_locators,
          paths_digest=paths_digest, hits=0, **common)
