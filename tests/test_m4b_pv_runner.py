"""Portable coverage for the canonical independent single-PV commands."""
from __future__ import annotations

import importlib.util
import asyncio
import json
import struct
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def pv_runner():
    path = Path(__file__).resolve().parents[1] / "scripts/run-m4b-pv.py"
    spec = importlib.util.spec_from_file_location("m4b_pv_runner_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _init_args(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(pv_run_id="pv-new", public_root=tmp_path / "public",
        private_root=tmp_path / "private", binding_manifest=tmp_path / "private/binding.json")


def test_runner_audio_output_applies_exact_quarter_gain(pv_runner):
    class Output:
        def __init__(self):
            self._observe = None
            self.started = self.stopped = False
            self.chunks = []

        async def start(self):
            self.started = True

        async def stop(self):
            self.stopped = True

        async def play(self, pcm):
            async for chunk in pcm:
                self.chunks.append(chunk)

    async def scenario():
        source = Output()
        output = pv_runner._QuarterVolumeAudioOutput(source)
        marker = object()
        output._observe = marker

        async def pcm():
            yield struct.pack("<7h", -32768, -5, -3, 0, 3, 5, 32767)

        await output.start()
        await output.play(pcm())
        await output.stop()
        assert source.started and source.stopped and source._observe is marker
        assert struct.unpack("<7h", source.chunks[0]) == (
            -8192, -1, 0, 0, 0, 1, 8191)

    asyncio.run(scenario())


@pytest.mark.parametrize("chunk", [b"x", bytearray(b"xx")], ids=["partial", "non-bytes"])
def test_runner_audio_gain_rejects_invalid_pcm(chunk, pv_runner):
    with pytest.raises(ValueError, match="complete S16_LE"):
        pv_runner._QuarterVolumeAudioOutput._scale(chunk)


def test_init_binds_new_empty_roots_without_selecting_obsolete_output(
        tmp_path, monkeypatch, pv_runner):
    args = _init_args(tmp_path)
    obsolete = tmp_path / "old-pm-result.json"
    obsolete.write_text('{"status":"Pass","threshold":1}')
    expected = {"schema_version": 1, "harness_sha256": "a" * 64,
        "content_sha256": "b" * 64, "profile_sha256": "c" * 64,
        "target_identity": pv_runner.TARGET_ID}
    monkeypatch.setattr(pv_runner, "_target_paths", lambda: {"product_profile": "profile"})
    monkeypatch.setattr(pv_runner, "_target_facts", lambda: {"machine": "aarch64"})
    monkeypatch.setattr(pv_runner, "_attest", lambda paths, private:
        ({}, expected, object(), object(), SimpleNamespace(digest="d" * 64)))
    monkeypatch.setattr(pv_runner.subprocess, "run", lambda *args, **kwargs:
        SimpleNamespace(stdout="e" * 40))

    assert pv_runner._init(args) == 0
    private = json.loads(args.binding_manifest.read_text())
    public = json.loads((args.public_root / "pv-init.json").read_text())
    assert private["expected_tuple"] == public["expected_tuple"] == expected
    assert private["public_root"] == str(args.public_root.resolve())
    assert private["private_root"] == str(args.private_root.resolve())
    assert private["base_sha"] == public["base_sha"] == "e" * 40
    assert "old-pm-result" not in args.binding_manifest.read_text()
    assert "threshold" not in (args.public_root / "pv-init.json").read_text()
    assert oct(args.binding_manifest.stat().st_mode & 0o777) == "0o600"


@pytest.mark.parametrize("occupied", ["public", "private", "binding"])
def test_init_rejects_reused_output(tmp_path, pv_runner, occupied):
    args = _init_args(tmp_path)
    if occupied == "binding":
        args.private_root.mkdir(mode=0o700)
        args.binding_manifest.write_text("old")
    else:
        root = getattr(args, occupied + "_root")
        root.mkdir(mode=0o700 if occupied == "private" else 0o755)
        (root / "old-result").write_text("old")
    with pytest.raises(pv_runner.PVError, match="PARTITION_NOT_EMPTY"):
        pv_runner._init(args)


def test_binding_reauthentication_rejects_content_drift(tmp_path, monkeypatch, pv_runner):
    args = _init_args(tmp_path)
    args.public_root.mkdir(mode=0o755)
    args.private_root.mkdir(mode=0o700)
    expected = {"schema_version": 1, "harness_sha256": "a" * 64,
        "content_sha256": "b" * 64, "profile_sha256": "c" * 64,
        "target_identity": pv_runner.TARGET_ID}
    binding = {"schema_version": 1, "pv_run_id": args.pv_run_id,
        "public_root": str(args.public_root.resolve()), "private_root": str(args.private_root.resolve()),
        "paths": {"product_profile": "profile"}, "expected_tuple": expected,
        "target_facts": {"machine": "aarch64"}, "artifact_lock_sha256": "d" * 64,
        "base_sha": "e" * 40, "status": "Initialized"}
    args.binding_manifest.write_text(json.dumps(binding))
    monkeypatch.setattr(pv_runner, "_target_facts", lambda: binding["target_facts"])
    changed = expected | {"content_sha256": "f" * 64}
    monkeypatch.setattr(pv_runner, "_attest", lambda paths, private:
        ({}, changed, object(), object(), SimpleNamespace(digest="d" * 64)))
    with pytest.raises(pv_runner.PVError, match="BINDING_DRIFT"):
        pv_runner._load_binding(SimpleNamespace(binding_manifest=args.binding_manifest,
                                                 pv_run_id=args.pv_run_id))


def _semantic_args(tmp_path: Path, case_id: str, utterance: str) -> SimpleNamespace:
    return SimpleNamespace(test_id="M4B-PI-SEM-001", case_id=case_id, utterance=utterance,
        pv_run_id="pv-new", sub_run_id="semantic-1", case_attempt_id="attempt-1",
        public_partition=tmp_path / "public/case", private_partition=tmp_path / "private/case",
        binding_manifest=tmp_path / "private/binding.json", fresh_setup=True,
        fresh_conversation=True)


@pytest.mark.parametrize("case_id,utterance", [
    ("S01-IDENTITY", "你是誰？"),
    ("S02-ENGLISH", "想要英文進步應該怎麼做？"),
    ("S03-SEVEN-DAYS", "為什麼一個星期有七天？"),
])
def test_semantic_case_uses_fresh_partitions_and_only_human_verdict(
        tmp_path, monkeypatch, pv_runner, case_id, utterance):
    public_root, private_root = tmp_path / "public", tmp_path / "private"
    public_root.mkdir(mode=0o755)
    private_root.mkdir(mode=0o700)
    args = _semantic_args(tmp_path, case_id, utterance)
    expected = {"content_sha256": "a" * 64}
    monkeypatch.setattr(pv_runner, "_load_binding",
        lambda values: ({"paths": {}}, public_root.resolve(), private_root.resolve()))
    monkeypatch.setattr(pv_runner, "_build_components",
        lambda binding, private, recorder: (object(), 10.0, expected))

    class Session:
        def __init__(self, components, recorder, *, timeout):
            assert timeout == 10.0

        async def run(self):
            return {"answer": "deliberately unsuitable fake answer"}

    monkeypatch.setattr(pv_runner, "_SemanticSession", Session)
    monkeypatch.setattr(pv_runner, "_semantic_native_proof",
        lambda private, capture: {"response_format": "json"})
    monkeypatch.setattr(pv_runner, "_human_verdict", lambda: "Pass")
    assert pv_runner._run_semantic_case(args) == 0
    card = json.loads((args.public_partition / "result.json").read_text())
    capture = json.loads((args.private_partition / "semantic-capture.json").read_text())
    assert card["status"] == card["user_verdict"] == card["automated_status"] == "Pass"
    assert card["case_id"] == case_id and capture["case_id"] == case_id
    assert capture["answer"] == "deliberately unsuitable fake answer"
    assert "answer" not in card and utterance not in json.dumps(card, ensure_ascii=False)
    assert oct((args.private_partition / "semantic-capture.json").stat().st_mode & 0o777) == "0o600"


def test_semantic_human_fail_is_not_overridden_by_structural_success(
        tmp_path, monkeypatch, pv_runner):
    public_root, private_root = tmp_path / "public", tmp_path / "private"
    public_root.mkdir(mode=0o755)
    private_root.mkdir(mode=0o700)
    args = _semantic_args(tmp_path, "S01-IDENTITY", "你是誰？")
    monkeypatch.setattr(pv_runner, "_load_binding",
        lambda values: ({"paths": {}}, public_root.resolve(), private_root.resolve()))
    monkeypatch.setattr(pv_runner, "_build_components",
        lambda binding, private, recorder: (object(), 10.0, {"content_sha256": "a" * 64}))

    class Session:
        def __init__(self, *args, **kwargs):
            pass

        async def run(self):
            return {"answer": "structurally complete"}

    monkeypatch.setattr(pv_runner, "_SemanticSession", Session)
    monkeypatch.setattr(pv_runner, "_semantic_native_proof",
        lambda private, capture: {"response_format": "json"})
    monkeypatch.setattr(pv_runner, "_human_verdict", lambda: "Fail")
    assert pv_runner._run_semantic_case(args) == 1
    assert json.loads((args.public_partition / "result.json").read_text())["status"] == "Fail"


def test_semantic_native_proof_requires_exact_json_schema_normal_answer(
        tmp_path, pv_runner):
    from sbd.cognition.semantic import RESPONSE_SCHEMA_LOCATOR, RESPONSE_SCHEMA_SHA256
    rows = [
        {"stage": "native_runtime_ready"},
        {"stage": "response_format_selected", "kind": "json",
         "response_schema_locator": RESPONSE_SCHEMA_LOCATOR,
         "response_schema_sha256": RESPONSE_SCHEMA_SHA256},
        {"stage": "native_generate_returned"},
        {"stage": "native_output", "raw_json":
         '{\n"text":"我是雪板，很高興為您服務！",\n"end":false}'},
        {"stage": "native_generate_metrics"},
    ]
    (tmp_path / "llm-child-1-events.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    capture = {
        "ready_identity": {"response_schema_locator": RESPONSE_SCHEMA_LOCATOR,
                           "response_schema_sha256": RESPONSE_SCHEMA_SHA256},
        "response": {"action_kind": "speak",
                     "action_payload": {"text": "我是雪板,很高興為您服務!"},
                     "post_action_route": "KEEP_NEXT"},
    }
    proof = pv_runner._semantic_native_proof(tmp_path, capture)
    assert proof["response_format"] == "json"
    assert proof["response_schema_locator"] == RESPONSE_SCHEMA_LOCATOR
    assert proof["response_format_call_count"] == proof["native_output_count"] == 1
    assert proof["normalized_text"] == "我是雪板,很高興為您服務!"

    rows[3]["raw_json"] = '{"text":"","end":false}'
    (tmp_path / "llm-child-1-events.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    capture["response"]["action_payload"] = {"text": ""}
    with pytest.raises(pv_runner.PVError, match="NATIVE_PATH_UNPROVEN"):
        pv_runner._semantic_native_proof(tmp_path, capture)


@pytest.mark.asyncio
async def test_semantic_session_runs_real_worker_orchestration_and_proves_cleanup(
        tmp_path, monkeypatch, pv_runner):
    from scripts.m4b_measurement import _DiagnosticRecorder
    from tests.test_m4b_measurement_harness import _live_worker_session
    measurement_session, _children, calls = _live_worker_session()
    recorder = _DiagnosticRecorder(tmp_path)
    subscribers_before = {kind: tuple(records)
                          for kind, records in measurement_session._c.bus._subscribers.items()}
    monkeypatch.setattr(pv_runner, "_native_cleanup_proven", lambda components, handles: True)
    try:
        result = await pv_runner._SemanticSession(
            measurement_session._c, recorder, timeout=10.0).run()
    finally:
        recorder.close()
    assert result["perception"]["status"] == "ok"
    assert result["response"]["action_kind"] == "speak"
    assert result["action"]["status"] == "ok"
    assert result["close_proof"]["cleanup_proven"] is True
    assert "played_pcm" in calls
    assert {kind: tuple(records) for kind, records
            in measurement_session._c.bus._subscribers.items()} == subscribers_before


@pytest.mark.asyncio
async def test_semantic_cleanup_failure_does_not_mask_startup_cause(
        tmp_path, monkeypatch, pv_runner):
    from scripts.m4b_measurement import _DiagnosticRecorder
    from tests.test_m4b_measurement_harness import _live_worker_session
    measurement_session, _children, _calls = _live_worker_session()
    recorder = _DiagnosticRecorder(tmp_path)

    async def fail_start():
        raise RuntimeError("audio startup cause")

    measurement_session._c.audio_input.start = fail_start
    monkeypatch.setattr(pv_runner, "_native_cleanup_proven", lambda components, handles: False)
    try:
        with pytest.raises(RuntimeError, match="audio startup cause"):
            await pv_runner._SemanticSession(
                measurement_session._c, recorder, timeout=10.0).run()
    finally:
        recorder.close()
    events = [json.loads(line) for line in
              (tmp_path / "diagnostic-events.jsonl").read_text().splitlines()]
    assert events[-1]["stage"] == "cleanup_failed"
    assert events[-1]["exception"] == "M4B_PV_CLEANUP_FAILED"


def test_pv_grant_crosses_child_with_automatic_attestation(tmp_path, monkeypatch):
    from sbd.cognition.litert_lm import measurement
    from sbd.cognition.litert_lm.lock import load_product_profile
    profile = load_product_profile(Path(__file__).parents[1] / "requirements/m4b/product-profile.json",
                                   allow_measurement=True)
    expected = {"schema_version": 1, "harness_sha256": "a" * 64,
        "content_sha256": "b" * 64, "profile_sha256": profile["profile_sha256"],
        "target_identity": "pi5-4gb-debian13-aarch64-cp3135"}
    calls = []
    monkeypatch.setattr(measurement, "_verify_context", lambda value: calls.append(dict(value)))
    grant = measurement.MeasurementGrant.pv(expected_tuple=expected, profile=profile,
                                             private_directory=tmp_path)
    assert grant.is_user_diagnostic() is False and calls == [expected]
    arguments = grant.child_arguments()
    assert arguments[:3] == ["--measurement-pv", "--measurement-private-directory", str(tmp_path)]
    assert arguments[3] == "--measurement-expected" and json.loads(arguments[4]) == expected


def test_protected_digest_includes_pending_new_file_bytes(tmp_path, monkeypatch):
    from sbd.cognition.litert_lm import measurement
    (tmp_path / "src").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "src/a.py").write_text("one")
    (tmp_path / "scripts/new.py").write_text("two")
    monkeypatch.setattr(measurement.subprocess, "run", lambda *args, **kwargs:
        SimpleNamespace(stdout=b"src/a.py\0scripts/new.py\0"))
    before = measurement.protected_content_digest(tmp_path)
    (tmp_path / "scripts/new.py").write_text("changed")
    changed = measurement.protected_content_digest(tmp_path)
    assert changed != before
    (tmp_path / "scripts/new.py").unlink()
    assert measurement.protected_content_digest(tmp_path) not in {before, changed}


def test_obsolete_stage_options_and_launchers_cannot_select_pv(pv_runner):
    assert pv_runner._obsolete_surface_absent() == {
        "obsolete_completion_flags_absent": True,
        "obsolete_bundle_validators_absent": True,
        "obsolete_launchers_absent": True,
        "canonical_entry_only": True,
    }
    for option in ("--complete-pm", "--validate-pm", "--release-rerun", "--ph"):
        with pytest.raises(SystemExit):
            pv_runner._parser().parse_args(["run", option])


def test_diagnostic_sampler_records_private_validation_reason(tmp_path, pv_runner):
    from scripts.m4b_measurement import _DiagnosticRecorder
    from sbd.cognition.litert_lm.resource import ResourceSampleError

    class Sampler:
        def sample(self, **_kwargs):
            raise ResourceSampleError("process_set_changed")

    recorder = _DiagnosticRecorder(tmp_path)
    try:
        sampler = pv_runner._DiagnosticResourceSampler(Sampler(), recorder)
        with pytest.raises(ResourceSampleError):
            sampler.sample(child_pid=1, child_pgid=1)
    finally:
        recorder.close()
    rows = [json.loads(line) for line in
            (tmp_path / "diagnostic-events.jsonl").read_text().splitlines()]
    assert rows[-1]["stage"] == "resource_sample_failed"
    assert rows[-1]["validation_reason"] == "process_set_changed"


def test_att_command_emits_assertion_level_card_after_child_cleanup(
        tmp_path, monkeypatch, pv_runner):
    from scripts import m4b_llm_product
    from sbd.cognition.litert_lm.lock import RuntimeFile
    public_root, private_root = tmp_path / "public", tmp_path / "private"
    public_root.mkdir(mode=0o755)
    private_root.mkdir(mode=0o700)
    args = SimpleNamespace(test_id="M4B-PI-ATT-001", pv_run_id="pv-new",
        sub_run_id="att-1", public_partition=public_root / "att",
        private_partition=private_root / "att", binding_manifest=private_root / "binding.json",
        fresh_setup=True, audio_fixture=None)
    expected = {"content_sha256": "a" * 64}
    from sbd.cognition.semantic import RESPONSE_SCHEMA_LOCATOR, RESPONSE_SCHEMA_SHA256
    profile = {"profile_id": "fixture", "response_schema_locator": RESPONSE_SCHEMA_LOCATOR,
               "response_schema_sha256": RESPONSE_SCHEMA_SHA256}
    lock = SimpleNamespace(digest="b" * 64, runtime={"api_version": "fixture"},
        model={"filename": "fixture"}, product_profile=profile,
        runtime_closure=SimpleNamespace(files=(
            RuntimeFile("runtime.py", 1, "c" * 64),)))
    binding = {"paths": {}, "target_facts": {"machine": "aarch64"}}
    monkeypatch.setattr(pv_runner, "_load_binding",
        lambda values: (binding, public_root.resolve(), private_root.resolve()))
    monkeypatch.setattr(pv_runner, "_attest", lambda paths, private:
        (profile, expected, object(), object(), lock))
    monkeypatch.setattr(pv_runner, "_obsolete_surface_absent", lambda: {"canonical_entry_only": True})
    abi = SimpleNamespace(sha256="d" * 64, as_dict=lambda: {"version": "3.13.5"})
    monkeypatch.setattr(m4b_llm_product, "capture_python_abi", lambda path: abi)
    monkeypatch.setattr(m4b_llm_product, "validate_python_abi", lambda value: None)

    async def ready(_binding, private, _recorder):
        stages = ("artifact_lock_verified", "response_schema_verified",
            "runtime_closure_verified",
            "model_profile_verified", "network_denial_installed", "native_runtime_ready",
            "ready_emitting")
        (private / "llm-child-1-events.jsonl").write_text("".join(
            json.dumps({"stage": stage}) + "\n" for stage in stages))
        return {"expected_tuple": expected, "ready_identity": {
                    "conversation_state": "none",
                    "response_schema_locator": RESPONSE_SCHEMA_LOCATOR,
                    "response_schema_sha256": RESPONSE_SCHEMA_SHA256},
                "pid": 1, "pgid": 1}

    monkeypatch.setattr(pv_runner, "_att_engine_ready", ready)
    assert pv_runner._run_att(args) == 0
    card = json.loads((args.public_partition / "result.json").read_text())
    assert card["script_status"] == "Pass" and card["status"] == "NeedsDeveloperReview"
    assert (args.private_partition / "inspection-catalog.json").is_file()
    assert set(card["assertions"]) == {
        "A01-NEW-ROOTS", "A02-BOUND-TUPLE", "A03-target-runtime", "A04-artifacts",
        "A05-profile-ready", "A06-obsolete-stage-negative"}
    assert all(value == "Pass" for value in card["assertions"].values())
    assert card["cleanup_proven"] is True and "profile" not in card


@pytest.mark.asyncio
async def test_automated_lifecycle_keeps_one_conversation_then_normally_closes(
        tmp_path, monkeypatch, pv_runner):
    from scripts.m4b_measurement import _DiagnosticRecorder
    from tests.test_m4b_measurement_harness import _live_worker_session
    measurement_session, children, calls = _live_worker_session()
    recorder = _DiagnosticRecorder(tmp_path)
    monkeypatch.setattr(pv_runner, "_native_cleanup_proven", lambda components, handles: True)
    session = pv_runner._AutomatedLifecycleSession(measurement_session._c, recorder)
    try:
        result = await session.run()
    finally:
        recorder.close()
    assert result["final_generation"] == 1 and result["normal_close_completed"] is True
    assert result["observed_scope"] == "FINITE_TWO_TURN_NO_REPLACEMENT"
    assert [proof["generation"] for proof in result["close_proofs"]] == [1]
    assert all(proof[name] is True for proof in result["close_proofs"] for name in
               ("request_terminal_proven", "cleanup_proven", "engine_usable"))
    first, second = result["turns"]
    assert [row["label"] for row in result["turns"]] == ["C01-FIRST", "C02-CONTINUE"]
    assert second["text"] == "0001 請再補充一點。"
    assert second["revision_before"] == first["revision_after"]
    assert second["revision_after"] > second["revision_before"]
    assert first["snapshot"]["current_kv_tokens"] == 0
    assert second["snapshot"]["current_kv_tokens"] > 0
    assert (first["child_pid"], first["child_pgid"]) == (second["child_pid"], second["child_pgid"])
    assert children[0].runtime.opens == children[0].runtime.closes == 1
    assert children[0].runtime.sends == calls.count("played_pcm") == 2


@pytest.mark.asyncio
async def test_automated_lifecycle_early_model_end_is_incomplete_without_replay(
        tmp_path, monkeypatch, pv_runner):
    from scripts.m4b_measurement import _DiagnosticRecorder
    from tests.test_m4b_measurement_harness import _live_worker_session
    measurement_session, children, calls = _live_worker_session()
    recorder = _DiagnosticRecorder(tmp_path)
    monkeypatch.setattr(pv_runner, "_native_cleanup_proven", lambda components, handles: True)
    session = pv_runner._AutomatedLifecycleSession(measurement_session._c, recorder)
    original_turn = session._turn

    async def end_after_first(text, label):
        row = await original_turn(text, label)
        if label == "C01-FIRST":
            children[0].runtime.output = '{"text":"再見","end":true}'
        return row

    session._turn = end_after_first
    try:
        with pytest.raises(pv_runner.PVError, match="M4B_PV_CONTINUING_TURN_FAILED"):
            await session.run()
    finally:
        recorder.close()
    assert [row["label"] for row in session.turns] == ["C01-FIRST", "C02-CONTINUE"]
    assert session.turns[-1]["response"]["post_action_route"] == "END_SESSION"
    assert children[0].runtime.sends == calls.count("played_pcm") == 2
    assert children[0].runtime.opens == children[0].runtime.closes == 1
    assert session.capture is None and session.started == []


@pytest.mark.asyncio
async def test_mem_lifecycle_owns_complete_independent_series_and_estimates(
        tmp_path, monkeypatch, pv_runner):
    from scripts.m4b_measurement import _DiagnosticRecorder
    from scripts.m4b_target_metrics import MeasurementHarness
    from tests.test_m4b_measurement_harness import _live_worker_session

    old_session, children, _calls = _live_worker_session()
    components = old_session._c
    recorder = _DiagnosticRecorder(tmp_path)
    expected = {"schema_version": 1, "harness_sha256": "a" * 64,
        "content_sha256": "b" * 64, "profile_sha256": "c" * 64,
        "target_identity": "pi5-4gb-debian13-aarch64-cp3135"}
    session = None

    def sample():
        child = components.adapter._child
        assert child is not None
        return components.sampler.sample(child_pid=child.pid, child_pgid=child.pgid)

    async def cleanup():
        assert session is not None
        return await session._cleanup()

    harness = MeasurementHarness(authorization=None, expected_tuple=expected,
        pv_attested=True, sample=sample, cleanup=cleanup)
    monkeypatch.setattr(pv_runner, "_native_cleanup_proven", lambda components, handles: True)
    session = pv_runner._AutomatedLifecycleSession(
        components, recorder, measurement_harness=harness)
    try:
        result = await session.run()
    finally:
        recorder.close()
    assert result["measurement"]["status"] == "Measured"
    assert result["measurement"]["derived"]["min_mem_available_generate_bytes"] >= 512 * 1024**2
    labels = [point.lifecycle_point for point in harness.points]
    assert labels[0] == "engine_ready" and labels[-1] == "post_session_close"
    assert {"pre_generate", "post_generate", "pre_speak", "audio_completion",
            "primary_completion"}.issubset(labels)
    assert labels.count("pre_generate") == labels.count("post_generate") == 2
    assert labels.count("pre_speak") == labels.count("audio_completion") == 2
    assert not {"pre_replacement", "post_replacement"}.intersection(labels)
    assert harness.completed and harness.cleanup_proven
    assert children[0].runtime.opens == children[0].runtime.closes == 1


def test_mem_records_exact_setup_swap_total_without_zero_growth_verdict(pv_runner):
    setup = pv_runner._mem_swap_configuration(
        "MemTotal: 4146944 kB\nSwapTotal: 2097152 kB\n", "60\n")
    assert setup == {"swap_total_bytes": 2 * 1024**3, "vm_swappiness": 60}
    with pytest.raises(pv_runner.PVError, match="SWAP_CONFIGURATION_MISSING"):
        pv_runner._mem_swap_configuration("MemTotal: 4146944 kB\n", "60")
    with pytest.raises(pv_runner.PVError, match="SWAP_CONFIGURATION_INVALID"):
        pv_runner._mem_swap_configuration("SwapTotal: 2097152 kB\n", "201")


def test_large_complete_mem_inspection_catalog_is_read_with_bounded_catalog_limit(
        tmp_path, pv_runner):
    catalog = tmp_path / "inspection-catalog.json"
    catalog.write_text(json.dumps({"fields": ["x" * (2 * 1024 * 1024)]}))
    with pytest.raises(pv_runner.PVError, match="BINDING_INVALID"):
        pv_runner._read_json(catalog)
    assert len(pv_runner._read_json(catalog, max_bytes=16 * 1024 * 1024)
               ["fields"][0]) == 2 * 1024 * 1024
    with pytest.raises(pv_runner.PVError, match="INSPECTION_CATALOG_INVALID"):
        pv_runner._read_json(catalog, max_bytes=2 * 1024 * 1024)


@pytest.mark.asyncio
async def test_fixed_audio_input_is_one_use_and_preserves_bound_pcm(tmp_path, pv_runner):
    from scripts.m4b_measurement import _DiagnosticRecorder
    fixture = tmp_path / "short-taiwan.wav"
    with wave.open(str(fixture), "wb") as output:
        output.setparams((1, 2, 16000, 320, "NONE", "not compressed"))
        output.writeframes(b"\x01\x02" * 320)
    recorder = _DiagnosticRecorder(tmp_path)
    try:
        audio = pv_runner._FixedAudioInput(fixture, recorder)
        await audio.start()
        stream = audio.frames()
        assert b"".join([chunk async for chunk in stream]) == b"\x01\x02" * 320
        with pytest.raises(pv_runner.PVError, match="AUDIO_FIXTURE_INVALID"):
            audio.frames()
        await audio.stop()
    finally:
        recorder.close()
    rows = [json.loads(line) for line in
            (tmp_path / "diagnostic-events.jsonl").read_text().splitlines()]
    assert rows[-1]["stage"] == "fixed_audio_consumed"
    assert rows[-1]["complete"] is True and rows[-1]["pcm_bytes"] == 640


def test_fixed_audio_input_rejects_partial_twenty_ms_frame(tmp_path, pv_runner):
    from scripts.m4b_measurement import _DiagnosticRecorder
    fixture = tmp_path / "partial.wav"
    with wave.open(str(fixture), "wb") as output:
        output.setparams((1, 2, 16000, 1, "NONE", "not compressed"))
        output.writeframes(b"\x01\x02")
    recorder = _DiagnosticRecorder(tmp_path)
    try:
        with pytest.raises(pv_runner.PVError, match="AUDIO_FIXTURE_INVALID"):
            pv_runner._FixedAudioInput(fixture, recorder)
    finally:
        recorder.close()


def test_bound_fixed_audio_fixture_contains_only_complete_twenty_ms_frames():
    fixture = Path(__file__).parent / "fixtures/m4b/pv/short-taiwan.wav"
    with wave.open(str(fixture), "rb") as source:
        assert (source.getnchannels(), source.getsampwidth(), source.getframerate(),
                source.getcomptype()) == (1, 2, 16000, "NONE")
        pcm_bytes = source.getnframes() * source.getsampwidth() * source.getnchannels()
        assert pcm_bytes > 0 and pcm_bytes % 640 == 0


def test_time_command_emits_one_clock_card_for_exact_fixture(
        tmp_path, monkeypatch, pv_runner):
    public_root, private_root = tmp_path / "public", tmp_path / "private"
    public_root.mkdir()
    private_root.mkdir(mode=0o700)
    fixture = tmp_path / "tests/fixtures/m4b/pv/short-taiwan.wav"
    fixture.parent.mkdir(parents=True)
    with wave.open(str(fixture), "wb") as output:
        output.setparams((1, 2, 16000, 320, "NONE", "not compressed"))
        output.writeframes(b"\x01\x02" * 320)
    args = SimpleNamespace(test_id="M4B-PI-TIME-001", pv_run_id="pv-new",
        sub_run_id="time-1", public_partition=public_root / "time",
        private_partition=private_root / "time", binding_manifest=private_root / "binding.json",
        fresh_setup=True, audio_fixture=fixture)
    expected = {"content_sha256": "a" * 64}
    monkeypatch.setattr(pv_runner, "ROOT", tmp_path)
    monkeypatch.setattr(pv_runner, "_load_binding",
        lambda values: ({"paths": {}}, public_root.resolve(), private_root.resolve()))
    monkeypatch.setattr(pv_runner, "_build_components",
        lambda *values: (object(), 10.0, expected))

    class Session:
        def __init__(self, components, audio, recorder, *, timeout):
            assert timeout == 10.0

        async def run(self):
            events = {name: {"monotonic_ns": index, "null_reason": None}
                      for index, name in enumerate(("conversation_ready", "asr_final",
                          "llm_send", "first_safe_text", "llm_terminal",
                          "tts_pcm_ready", "audio_first_write"), 1)}
            return {"timing": {"clock_domain": "controller_monotonic", "events": events},
                    "runtime": {}, "perception": {}, "response": {}, "action": {},
                    "close_proof": {}, "frame_pull_count": 1}

    monkeypatch.setattr(pv_runner, "_FixedAudioSession", Session)
    assert pv_runner._run_time(args) == 0
    card = json.loads((args.public_partition / "result.json").read_text())
    assert card["script_status"] == "Pass" and card["status"] == "NeedsDeveloperReview"
    assert card["clock_mapping_verified"] is True
    assert set(card["assertions"]) == {"T01-FIXED-AUDIO", "T02-CLOCK-MAP",
                                       "T03-NODE-ORDER", "T04-NULL-REASON"}


@pytest.mark.parametrize("case_id", [
    "W01-OPEN-FIRST", "W02-ACK-FIRST", "W03-SLOW-OPEN", "W04-INTERRUPT-OPEN",
])
def test_wake_cases_use_production_sm_ingress_and_exclude_pre_barrier_activity(
        tmp_path, monkeypatch, pv_runner, case_id):
    from scripts.m4b_measurement import _DiagnosticRecorder
    from sbd.core.config.defaults import DEFAULT_CONFIG
    from tests.test_m4b_measurement_harness import _live_worker_session

    measurement_session, children, _calls = _live_worker_session()
    recorder = _DiagnosticRecorder(tmp_path)
    monkeypatch.setattr(pv_runner, "_native_cleanup_proven",
                        lambda components, handles: bool(handles))
    try:
        session = pv_runner._WakePathSession(
            measurement_session._c, DEFAULT_CONFIG, recorder,
            case_id=case_id, listen_timeout=0.5)
        result = asyncio.run(session.run())
    finally:
        recorder.close()
    assert result["case_id"] == case_id and session.cleanup_proven is True
    assert result["production_path"]["state_manager"] == "StateManager"
    assert result["production_path"]["button_source"] == "ButtonInputSource"
    assert result["display"]["state_slot_only"] is True
    if case_id == "W04-INTERRUPT-OPEN":
        assert result["activity"] == []
        assert children[0].runtime.opens == children[0].runtime.closes == 1
    else:
        assert pv_runner._WakeTrace.ACTIVITY_STAGES == {
            row["stage"] for row in result["activity"]}
        barrier = max(value for key, value in result["barriers"].items()
                      if key != "bounded_open_delay_ns")
        assert min(row["monotonic_ns"] for row in result["activity"]) >= barrier


def test_wake_command_emits_one_independent_case_card(
        tmp_path, monkeypatch, pv_runner):
    public_root, private_root = tmp_path / "public", tmp_path / "private"
    public_root.mkdir()
    private_root.mkdir(mode=0o700)
    audio_config = tmp_path / "audio.yaml"
    audio_config.write_text("{}")
    expected = {"content_sha256": "a" * 64}
    args = SimpleNamespace(test_id="M4B-PI-WAKE-001", case_id="W02-ACK-FIRST",
        pv_run_id="pv-new", sub_run_id="wake-2", case_attempt_id="wake-attempt-2",
        public_partition=public_root / "wake", private_partition=private_root / "wake",
        binding_manifest=private_root / "binding.json", fresh_setup=True,
        production_wake_path=True)
    monkeypatch.setattr(pv_runner, "_load_binding", lambda values:
        ({"paths": {"audio_config": str(audio_config)}},
         public_root.resolve(), private_root.resolve()))
    monkeypatch.setattr(pv_runner, "_build_components",
                        lambda *values: (object(), 10.0, expected))

    class Session:
        def __init__(self, components, config, recorder, *, case_id, listen_timeout):
            self.cleanup_proven = True

        async def run(self):
            activity = [{"stage": stage, "monotonic_ns": index}
                        for index, stage in enumerate(sorted(
                            pv_runner._WakeTrace.ACTIVITY_STAGES), 10)]
            return {"case_id": "W02-ACK-FIRST",
                "barriers": {"wake_acknowledged": 1, "conversation_joined": 2},
                "activity": activity, "trace": activity,
                "display": {"state_slot_only": True},
                "production_path": {"state_manager": "StateManager"}}

    monkeypatch.setattr(pv_runner, "_WakePathSession", Session)
    assert pv_runner._run_wake_case(args) == 0
    card = json.loads((args.public_partition / "result.json").read_text())
    capture = json.loads((args.private_partition / "wake-capture.json").read_text())
    assert card["status"] == "Pass" and card["case_id"] == "W02-ACK-FIRST"
    assert set(card["assertions"]) == {"W02-ACK-FIRST", "W00-PRODUCTION-PATH",
        "W00-PRE-BARRIER-EXCLUSION", "W00-DISPLAY-NONBLOCKING", "W00-CLEANUP"}
    assert capture["case_attempt_id"] == "wake-attempt-2"
    assert oct((args.private_partition / "wake-capture.json").stat().st_mode & 0o777) == "0o600"


def _resource_args(tmp_path, case_id):
    return SimpleNamespace(test_id="M4B-PI-RES-001", case_id=case_id,
        pv_run_id="pv-new", sub_run_id=f"res-{case_id.lower()}",
        case_attempt_id=f"attempt-{case_id.lower()}",
        public_partition=tmp_path / f"public/{case_id}",
        private_partition=tmp_path / f"private/{case_id}",
        binding_manifest=tmp_path / "private/binding.json", fresh_setup=True)


def _resource_samples(count=5):
    processes = [
        {"pid": 10, "owner": ["core", "vad"], "start_time_ticks": 1,
         "pss_bytes": 1, "rss_bytes": 2, "cpu_seconds": 0.0, "threads": 1},
        {"pid": 11, "owner": ["asr"], "start_time_ticks": 2,
         "pss_bytes": 1, "rss_bytes": 2, "cpu_seconds": 0.0, "threads": 1},
        {"pid": 12, "owner": ["tts"], "start_time_ticks": 3,
         "pss_bytes": 1, "rss_bytes": 2, "cpu_seconds": 0.0, "threads": 1},
        {"pid": 13, "owner": ["llm"], "start_time_ticks": 4,
         "pss_bytes": 1, "rss_bytes": 2, "cpu_seconds": 0.0, "threads": 1},
    ]
    sample = {"monotonic_ns": 1, "processes": processes,
        "mem_total_bytes": 4 * 1024**3, "mem_available_bytes": 2 * 1024**3,
        "swap_used_bytes": 0, "oom_kill": 0, "temperature_c": 50.0,
        "throttled_bits": 0}
    return [{"label": f"point-{index}", "sample": {**sample,
             "monotonic_ns": index + 1}} for index in range(count)]


def test_resource_health_and_pid_summaries_reject_unsafe_or_changed_rows(pv_runner):
    capture = {"samples": _resource_samples()}
    assert pv_runner._resource_health_summary(capture)["sample_count"] == 5
    assert pv_runner._resource_pid_summary(capture)["owners"] == [
        "asr", "core", "llm", "tts", "vad"]
    unsafe = json.loads(json.dumps(capture))
    unsafe["samples"][2]["sample"]["temperature_c"] = 80.0
    with pytest.raises(pv_runner.PVError, match="HEALTH_UNSAFE"):
        pv_runner._resource_health_summary(unsafe)
    changed = json.loads(json.dumps(capture))
    changed["samples"][3]["sample"]["processes"][3]["pid"] = 99
    with pytest.raises(pv_runner.PVError, match="PID_INVALID"):
        pv_runner._resource_pid_summary(changed)


def test_resource_health_reports_active_zram_growth_without_forcing_failure(pv_runner):
    capture = {"samples": _resource_samples()}
    capture["samples"][2]["sample"]["swap_used_bytes"] = 2 * 1024**2
    capture["samples"][3]["sample"]["swap_used_bytes"] = 18 * 1024**2
    capture["samples"][4]["sample"]["swap_used_bytes"] = 14 * 1024**2
    summary = pv_runner._resource_health_summary(capture)
    assert summary["swap_growth_bytes"] == 18 * 1024**2
    assert summary["oom_growth"] == 0
    assert summary["min_mem_available_bytes"] == 2 * 1024**3


def test_resource_network_trace_rejects_outbound_dns_and_downloaders(pv_runner):
    clean = [("trace.1", b'socket(AF_UNIX, SOCK_STREAM, 0) = 3\n'
                           b'connect(3, {sa_family=AF_INET, sin_port=htons(1), '
                           b'sin_addr=inet_addr("127.0.0.1")}, 16) = 0\n'
                           b'execve("/usr/bin/git", ["git", "ls-files"], 0x0) = 0\n')]
    assert pv_runner._network_trace_violations(clean) == []
    bad = [("trace.2", b'connect(3, {sa_family=AF_INET, sin_port=htons(53), '
                         b'sin_addr=inet_addr("8.8.8.8")}, 16) = -1\n'
                         b'execve("/usr/bin/curl", ["curl"], 0x0) = 0\n'
                         b'execve("/usr/bin/git", ["git", "clone"], 0x0) = 0\n')]
    assert pv_runner._network_trace_violations(bad) == [
        "trace.2:1", "trace.2:2", "trace.2:3"]


@pytest.mark.parametrize("case_id", [
    "R02-HEALTH", "R03-PID", "R08-PRIVACY",
])
def test_resource_structural_commands_emit_independent_sanitized_cards(
        tmp_path, monkeypatch, pv_runner, case_id):
    public_root, private_root = tmp_path / "public", tmp_path / "private"
    public_root.mkdir(mode=0o755)
    private_root.mkdir(mode=0o700)
    expected = {"content_sha256": "a" * 64}
    monkeypatch.setattr(pv_runner, "_load_binding", lambda values:
        ({"expected_tuple": expected, "paths": {}},
         public_root.resolve(), private_root.resolve()))
    monkeypatch.setattr(pv_runner, "_build_components",
                        lambda *values, **kwargs: (object(), 10.0, expected))
    monkeypatch.setattr(pv_runner, "_partition_holders", lambda *roots: [])

    class Session:
        def __init__(self, components, recorder, *, text, redact_content=False):
            self.cleanup_proven = True
            self.process_blobs = []
            self.workdirs = []

        async def run(self):
            return {"samples": _resource_samples(),
                "close_proof": {"cleanup_proven": True},
                "input": {"codepoints": 1, "sha256": "b" * 64},
                "answer": {"codepoints": 1, "sha256": "c" * 64}}

    monkeypatch.setattr(pv_runner, "_ResourceStructuralSession", Session)
    if case_id == "R02-HEALTH":
        monkeypatch.setattr("scripts.m4b_target_metrics.kernel_resource_sample",
                            lambda *values: {"swap_total_mib": 2048})
        monkeypatch.setattr("sbd.core._m4b_resource_binding._pi_temperature",
                            lambda: 50.0)
        monkeypatch.setattr("sbd.core._m4b_resource_binding._pi_throttled",
                            lambda: 0)
    args = _resource_args(tmp_path, case_id)
    assert pv_runner._run_resource_case(args) == 0
    card = json.loads((args.public_partition / "result.json").read_text())
    capture = json.loads((args.private_partition / "resource-capture.json").read_text())
    assert card["status"] == "Pass" and card["case_id"] == case_id
    assert all(value == "Pass" for value in card["assertions"].values())
    if case_id == "R02-HEALTH":
        assert capture["swap_configuration"] == {"swap_total_mib": 2048}
        assert "R02-SWAP-OOM" not in card["assertions"]
        assert card["assertions"]["R02-OOM"] == "Pass"
    assert "private_content" not in capture
    assert oct((args.private_partition / "resource-capture.json").stat().st_mode & 0o777) == "0o600"


@pytest.mark.parametrize("case_id,method", [
    ("R06-FORCED-CLEANUP", "run_forced_cleanup"),
    ("R07-SHUTDOWN", "run_shutdown"),
])
def test_resource_owner_only_commands_keep_forced_cleanup_and_shutdown_separate(
        tmp_path, monkeypatch, pv_runner, case_id, method):
    public_root, private_root = tmp_path / "public", tmp_path / "private"
    public_root.mkdir(mode=0o755)
    private_root.mkdir(mode=0o700)
    expected = {"content_sha256": "a" * 64}
    monkeypatch.setattr(pv_runner, "_load_binding", lambda values:
        ({"expected_tuple": expected, "paths": {}},
         public_root.resolve(), private_root.resolve()))
    monkeypatch.setattr(pv_runner, "_build_components",
                        lambda *values, **kwargs: (object(), 10.0, expected))
    monkeypatch.setattr(pv_runner, "_partition_holders", lambda *roots: [])

    class Session:
        def __init__(self, *values, **kwargs):
            self.cleanup_proven = True

        async def run_forced_cleanup(self):
            return {"remaining_members": 0, "rebuild_attempted": False}

        async def run_shutdown(self):
            return {"live_sampler": True, "live_child_count": 3,
                    "sampler_stopped": True,
                    "shutdown_invoked_with_sampler_live": True}

    monkeypatch.setattr(pv_runner, "_ResourceOwnerSession", Session)
    args = _resource_args(tmp_path, case_id)
    assert pv_runner._run_resource_case(args) == 0
    card = json.loads((args.public_partition / "result.json").read_text())
    assert card["status"] == "Pass" and case_id in card["assertions"]
    if method == "run_forced_cleanup":
        assert "R06-NO-REBUILD" in card["assertions"]
        assert "R05-FOLLOWING-TURN" not in card["assertions"]


def test_resource_recovery_command_requires_sm_order_ready_and_following_turn(
        tmp_path, monkeypatch, pv_runner):
    import sbd.core.config.loader as config_loader
    public_root, private_root = tmp_path / "public", tmp_path / "private"
    public_root.mkdir(mode=0o755)
    private_root.mkdir(mode=0o700)
    expected = {"content_sha256": "a" * 64}
    monkeypatch.setattr(pv_runner, "_load_binding", lambda values:
        ({"expected_tuple": expected, "paths": {"audio_config": "unused"}},
         public_root.resolve(), private_root.resolve()))
    monkeypatch.setattr(pv_runner, "_build_components",
                        lambda *values, **kwargs: (object(), 10.0, expected))
    monkeypatch.setattr(config_loader, "load_config", lambda **kwargs: object())

    class Session:
        def __init__(self, components, config, recorder, coordinator):
            self.cleanup_proven = True

        async def run(self):
            return {"sm_authorization_count": 1, "new_ready": True,
                    "following_structural_turn": True,
                    "following_source": "real_reasoner",
                    "following_generated": True, "ledger": []}

    monkeypatch.setattr(pv_runner, "_ResourceRecoverySession", Session)
    args = _resource_args(tmp_path, "R05-RECOVERY")
    assert pv_runner._run_resource_case(args) == 0
    card = json.loads((args.public_partition / "result.json").read_text())
    assert set(card["assertions"]) == {"R05-RECOVERY", "R05-ACTION-REST-CLOSE",
        "R05-SM-AUTHORIZATION", "R05-NEW-READY", "R05-FOLLOWING-TURN", "R00-CLEANUP"}


def test_resource_normal_close_command_uses_product_session(
        tmp_path, monkeypatch, pv_runner):
    import sbd.core.config.loader as config_loader
    public_root, private_root = tmp_path / "public", tmp_path / "private"
    public_root.mkdir(mode=0o755)
    private_root.mkdir(mode=0o700)
    expected = {"content_sha256": "a" * 64}
    monkeypatch.setattr(pv_runner, "_load_binding", lambda values:
        ({"expected_tuple": expected, "paths": {"audio_config": "unused"}},
         public_root.resolve(), private_root.resolve()))
    monkeypatch.setattr(pv_runner, "_build_components",
                        lambda *values, **kwargs: (object(), 10.0, expected))
    monkeypatch.setattr(config_loader, "load_config", lambda **kwargs: object())

    class Session:
        def __init__(self, components, config, recorder, coordinator=None):
            assert coordinator is None
            self.cleanup_proven = True

        async def run_normal_close(self):
            return {"product_session_closed": True,
                    "close_proof": {"cleanup_proven": True}, "ledger": []}

    monkeypatch.setattr(pv_runner, "_ResourceRecoverySession", Session)
    args = _resource_args(tmp_path, "R04-NORMAL-CLOSE")
    assert pv_runner._run_resource_case(args) == 0
    card = json.loads((args.public_partition / "result.json").read_text())
    assert "R04-PRODUCT-SESSION" in card["assertions"]


def test_resource_recovery_session_uses_real_sm_authorization_barrier(
        tmp_path, monkeypatch, pv_runner):
    from scripts.m4b_measurement import _DiagnosticRecorder
    from sbd.core.config.defaults import DEFAULT_CONFIG
    from tests.test_m4b_measurement_harness import _live_worker_session
    import scripts.m4b_target_metrics as target_metrics

    measurement_session, children, _calls = _live_worker_session()
    components = measurement_session._c
    components.observer.harness = None
    recorder = _DiagnosticRecorder(tmp_path)
    ledger = []
    coordinator = pv_runner._RecoveryCoordinator(recorder, ledger)
    coordinator.bind(components.adapter)
    components.adapter._schedule_recovery = coordinator.begin_recovery
    components.adapter._wait_recovery = coordinator.wait_recovery
    monkeypatch.setattr(target_metrics, "process_group_members", lambda pgid: set())
    session = pv_runner._ResourceRecoverySession(
        components, DEFAULT_CONFIG, recorder, coordinator)

    async def start_native_owners():
        session.started = [components.audio_input, components.audio_output,
                           components.listener, components.speaker, components.reasoner]
        for owner in session.started:
            await owner.start()
        session.handles = [components.adapter._child]

    async def cleanup_native_owners():
        for owner in reversed(session.started):
            await owner.stop()
        session.cleanup_proven = components.adapter._child is None

    session._start = start_native_owners
    session._cleanup = cleanup_native_owners
    try:
        result = asyncio.run(session.run())
    finally:
        recorder.close()
    stages = [row["stage"] for row in result["ledger"]]
    assert result["following_structural_turn"] is True
    assert stages.index("conversation_close_proven") < stages.index("sm_authorize_recovery")
    assert stages.index("sm_authorize_recovery") < stages.index("rebuild_start")
    assert stages.index("rebuild_start") < stages.index("new_ready")
    assert len(children) == 2 and children[0].terminated == 1
    assert children[1].runtime.sends == 1
    assert result["following_source"] == "real_reasoner"
    assert result["following_generated"] is True
    assert session.cleanup_proven is True


def test_resource_normal_close_session_uses_action_rest_and_product_close(
        tmp_path, pv_runner):
    from scripts.m4b_measurement import _DiagnosticRecorder
    from sbd.core.config.defaults import DEFAULT_CONFIG
    from tests.test_m4b_measurement_harness import _live_worker_session

    measurement_session, children, _calls = _live_worker_session()
    components = measurement_session._c
    components.observer.harness = None
    recorder = _DiagnosticRecorder(tmp_path)
    session = pv_runner._ResourceRecoverySession(
        components, DEFAULT_CONFIG, recorder)

    async def start_native_owners():
        session.started = [components.audio_input, components.audio_output,
                           components.listener, components.speaker, components.reasoner]
        for owner in session.started:
            await owner.start()
        session.handles = [components.adapter._child]

    async def cleanup_native_owners():
        for owner in reversed(session.started):
            await owner.stop()
        session.cleanup_proven = components.adapter._child is None

    session._start = start_native_owners
    session._cleanup = cleanup_native_owners
    try:
        result = asyncio.run(session.run_normal_close())
    finally:
        recorder.close()
    stages = [row["stage"] for row in result["ledger"]]
    assert result["product_session_closed"] is True
    assert result["recovery_authorized"] is False
    assert "planned_recovery_marked" not in stages
    assert children[0].runtime.opens == children[0].runtime.closes == 1
    assert session.cleanup_proven is True


def test_resource_shutdown_starts_live_sampler_before_owner_cleanup(
        tmp_path, pv_runner):
    from scripts.m4b_measurement import _DiagnosticRecorder
    from tests.test_m4b_measurement_harness import _live_worker_session

    measurement_session, _children, _calls = _live_worker_session()
    components = measurement_session._c
    components.observer.harness = None
    recorder = _DiagnosticRecorder(tmp_path)
    session = pv_runner._ResourceOwnerSession(components, recorder, text="")

    async def start_owner():
        session.started = [components.reasoner]
        await components.reasoner.start()
        session.handles = [components.adapter._child]

    async def cleanup_owner():
        await components.reasoner.stop()
        session.cleanup_proven = components.adapter._child is None

    session._start = start_owner
    session._cleanup = cleanup_owner
    try:
        result = asyncio.run(session.run_shutdown())
    finally:
        recorder.close()
    assert result["shutdown_invoked_with_sampler_live"] is True
    assert result["sampler_stopped"] is True
    assert session.cleanup_proven is True


def _write_pass_card(root, *, test_id, expected, case_id=None, attempt=None,
                     assertions=None, extra=None):
    root.mkdir(parents=True)
    card = {"schema_version": 1, "test_id": test_id, "pv_run_id": "pv-new",
            "sub_run_id": root.name, "expected_tuple": expected,
            "script_status": "Pass",
            "status": "Pass" if case_id is not None else "NeedsDeveloperReview"}
    if case_id is not None:
        card.update(case_id=case_id, case_attempt_id=attempt,
                    assertions=assertions or {case_id: "Pass"})
    if extra:
        card.update(extra)
    (root / "result.json").write_text(json.dumps(card))
    return card


def _write_case_capture(private_root, *, test_id, case_id, attempt, expected):
    partition = private_root / attempt
    partition.mkdir(parents=True, mode=0o700)
    name = ("wake-capture.json" if test_id == "M4B-PI-WAKE-001" else
            "offline-child-capture.json" if case_id == "R01-OFFLINE" else
            "resource-capture.json")
    (partition / name).write_text(json.dumps({"schema_version": 1,
        "pv_run_id": "pv-new", "test_id": test_id, "case_id": case_id,
        "case_attempt_id": attempt, "expected_tuple": expected,
        "event_count": 1, "cleanup_proven": True}))
    return partition


def _write_semantic_verdict(public_root, private_root, pv_runner, *,
                            case_id, attempt, expected, verdict="Pass"):
    root = public_root / attempt
    capture_root = private_root / attempt
    capture_root.mkdir(parents=True, mode=0o700)
    private_capture = capture_root / "semantic-capture.json"
    private_capture.write_text(json.dumps({"schema_version": 1,
        "pv_run_id": "pv-new", "test_id": "M4B-PI-SEM-001",
        "case_id": case_id, "case_attempt_id": attempt,
        "expected_tuple": expected, "native_path_proof": {"runtime": "litert-lm/Gemma"}}))
    card = _write_pass_card(root, test_id="M4B-PI-SEM-001",
        expected=expected, case_id=case_id, attempt=attempt,
        extra={"user_verdict": verdict, "status": verdict,
               "capture_sha256": pv_runner._sha256(private_capture)})
    captured = {**card, "user_verdict": None, "status": "NeedsHumanReview"}
    (root / "capture.json").write_text(json.dumps(captured))
    card["capture_card_sha256"] = pv_runner._sha256(root / "capture.json")
    (root / "result.json").write_text(json.dumps(card))
    return root / "result.json"


def _aggregate_args(tmp_path, test_id, suffix):
    return SimpleNamespace(test_id=test_id, pv_run_id="pv-new",
        public_partition=tmp_path / f"public/aggregate-{suffix}",
        private_partition=tmp_path / f"private/aggregate-{suffix}",
        binding_manifest=tmp_path / "private/binding.json")


def test_case_aggregation_selects_one_fresh_pass_per_required_case(
        tmp_path, monkeypatch, pv_runner):
    public_root, private_root = tmp_path / "public", tmp_path / "private"
    public_root.mkdir(mode=0o755)
    private_root.mkdir(mode=0o700)
    expected = {"content_sha256": "a" * 64}
    monkeypatch.setattr(pv_runner, "_load_binding",
        lambda args: ({"expected_tuple": expected}, public_root.resolve(), private_root.resolve()))
    for index, case_id in enumerate(pv_runner.AGGREGATE_CASES["M4B-PI-WAKE-001"]):
        attempt = f"attempt-{index}"
        _write_pass_card(public_root / f"case-{index}", test_id="M4B-PI-WAKE-001",
                         expected=expected, case_id=case_id, attempt=attempt)
        _write_case_capture(private_root, test_id="M4B-PI-WAKE-001",
                            case_id=case_id, attempt=attempt, expected=expected)
    args = _aggregate_args(tmp_path, "M4B-PI-WAKE-001", "wake")
    assert pv_runner._run_aggregate_cases(args) == 0
    card = json.loads((args.public_partition / "result.json").read_text())
    selection = json.loads((args.private_partition / "aggregate-selection.json").read_text())
    assert card["aggregate"] is True and card["script_status"] == "Pass"
    assert card["status"] == "NeedsDeveloperReview"
    assert (args.private_partition / "inspection-catalog.json").is_file()
    assert [row["case_id"] for row in card["cases"]] == list(
        pv_runner.AGGREGATE_CASES["M4B-PI-WAKE-001"])
    assert len(selection["selected_cases"]) == 4
    assert oct((args.private_partition / "aggregate-selection.json").stat().st_mode & 0o777) == "0o600"


def test_case_aggregation_rejects_duplicate_pass_for_one_case(
        tmp_path, monkeypatch, pv_runner):
    public_root, private_root = tmp_path / "public", tmp_path / "private"
    public_root.mkdir(mode=0o755)
    private_root.mkdir(mode=0o700)
    expected = {"content_sha256": "a" * 64}
    monkeypatch.setattr(pv_runner, "_load_binding",
        lambda args: ({"expected_tuple": expected}, public_root.resolve(), private_root.resolve()))
    required = pv_runner.AGGREGATE_CASES["M4B-PI-WAKE-001"]
    for index, case_id in enumerate(required):
        _write_pass_card(public_root / f"case-{index}", test_id="M4B-PI-WAKE-001",
                         expected=expected, case_id=case_id, attempt=f"attempt-{index}")
    _write_pass_card(public_root / "duplicate", test_id="M4B-PI-WAKE-001",
                     expected=expected, case_id=required[0], attempt="attempt-duplicate")
    with pytest.raises(pv_runner.PVError, match="CASE_SELECTION_INVALID"):
        pv_runner._run_aggregate_cases(_aggregate_args(
            tmp_path, "M4B-PI-WAKE-001", "wake"))


def test_fake_public_cards_without_private_evidence_cannot_finalize(
        tmp_path, monkeypatch, pv_runner):
    public_root, private_root = tmp_path / "public", tmp_path / "private"
    public_root.mkdir(mode=0o755)
    private_root.mkdir(mode=0o700)
    expected = {"content_sha256": "a" * 64}
    monkeypatch.setattr(pv_runner, "_load_binding",
        lambda args: ({"expected_tuple": expected}, public_root.resolve(), private_root.resolve()))
    for index, test_id in enumerate(("M4B-PI-ATT-001", "M4B-PI-CONV-001",
                                     "M4B-PI-MEM-001", "M4B-PI-TIME-001")):
        extra = {"assertions": {f"A{index}": "Pass"}}
        if test_id == "M4B-PI-MEM-001":
            extra.update(speak_drop_bytes=1, generate_drop_bytes=2,
                min_mem_available_speak_bytes=536870912,
                min_mem_available_generate_bytes=537919488)
        _write_pass_card(public_root / f"single-{index}", test_id=test_id,
                         expected=expected, extra=extra)
    for index, case_id in enumerate(pv_runner.SEMANTIC_CASES):
        _write_pass_card(public_root / f"semantic-{index}", test_id="M4B-PI-SEM-001",
                         expected=expected, case_id=case_id, attempt=f"semantic-attempt-{index}",
                         assertions=None, extra={"user_verdict": "Pass"})
    for test_id, suffix in (("M4B-PI-WAKE-001", "wake"),
                            ("M4B-PI-RES-001", "res")):
        for index, case_id in enumerate(pv_runner.AGGREGATE_CASES[test_id]):
            _write_pass_card(public_root / f"{suffix}-case-{index}", test_id=test_id,
                             expected=expected, case_id=case_id,
                             attempt=f"{suffix}-attempt-{index}")
        with pytest.raises(pv_runner.PVError, match="CASE_EVIDENCE_INCOMPLETE"):
            pv_runner._run_aggregate_cases(_aggregate_args(tmp_path, test_id, suffix))
    args = SimpleNamespace(pv_run_id="pv-new", public_root=public_root,
        private_root=private_root, binding_manifest=private_root / "binding.json")
    assert pv_runner._finalize(args) == 1
    assert json.loads((public_root / "pv-final.json").read_text())["pv_status"] == "Incomplete"


def _complete_inspection_fixture(tmp_path, monkeypatch, pv_runner):
    public_root, private_root = tmp_path / "public", tmp_path / "private"
    public_root.mkdir(mode=0o755)
    private_root.mkdir(mode=0o700)
    expected = {"content_sha256": "a" * 64}
    monkeypatch.setattr(pv_runner, "_load_binding",
        lambda args: ({"expected_tuple": expected}, public_root.resolve(), private_root.resolve()))
    catalogs = {}
    for index, test_id in enumerate(("M4B-PI-ATT-001", "M4B-PI-CONV-001",
                                     "M4B-PI-MEM-001", "M4B-PI-TIME-001")):
        card_dir = public_root / f"single-{index}"
        capture_dir = private_root / f"single-{index}"
        capture_dir.mkdir(mode=0o700)
        extra = {"assertions": {f"A{index}": "Pass"}}
        if test_id == "M4B-PI-MEM-001":
            extra.update(speak_drop_bytes=1, generate_drop_bytes=2,
                min_mem_available_speak_bytes=536870912,
                min_mem_available_generate_bytes=537919488)
        _write_pass_card(card_dir, test_id=test_id, expected=expected, extra=extra)
        capture_name = pv_runner._INSPECTION_CAPTURE[test_id]
        (capture_dir / capture_name).write_text(json.dumps({"schema_version": 1,
            "pv_run_id": "pv-new", "test_id": test_id, "expected_tuple": expected,
            "operation_count": index + 1, "cleanup_proven": True, "null_reason": None}))
        catalogs[test_id] = pv_runner._write_inspection_catalog(
            test_id=test_id, pv_run_id="pv-new", expected=expected,
            card_path=card_dir / "result.json", public_root=public_root,
            private_root=private_root, private_partition=capture_dir)
    for index, case_id in enumerate(pv_runner.SEMANTIC_CASES):
        _write_semantic_verdict(public_root, private_root, pv_runner,
            case_id=case_id, attempt=f"semantic-attempt-{index}", expected=expected)
    for test_id, suffix in (("M4B-PI-WAKE-001", "wake"),
                            ("M4B-PI-RES-001", "res")):
        for index, case_id in enumerate(pv_runner.AGGREGATE_CASES[test_id]):
            attempt = f"{suffix}-attempt-{index}"
            _write_pass_card(public_root / f"{suffix}-case-{index}",
                             test_id=test_id, expected=expected,
                             case_id=case_id, attempt=attempt)
            _write_case_capture(private_root, test_id=test_id,
                                case_id=case_id, attempt=attempt, expected=expected)
        aggregate = _aggregate_args(tmp_path, test_id, suffix)
        assert pv_runner._run_aggregate_cases(aggregate) == 0
        catalogs[test_id] = aggregate.private_partition / "inspection-catalog.json"
    return public_root, private_root, expected, catalogs


def _review_args(private_root, test_id, catalog_path, *, status="Pass",
                 failed_item="NONE", commentary="Every raw item inspected."):
    catalog = json.loads(catalog_path.read_text())
    return SimpleNamespace(test_id=test_id, pv_run_id="pv-new",
        binding_manifest=private_root / "binding.json",
        inspection_catalog=catalog_path, review_status=status,
        reviewed_field_count=catalog["expected_field_count"],
        reviewed_row_count=catalog["expected_row_count"],
        failed_item=failed_item, commentary=commentary)


def test_complete_catalog_reviews_finalize_without_public_private_notes(
        tmp_path, monkeypatch, pv_runner, capsys):
    public_root, private_root, _expected, catalogs = _complete_inspection_fixture(
        tmp_path, monkeypatch, pv_runner)
    canary = "PRIVATE-OUTPUT-CANARY-9c1b"
    for test_id, catalog_path in catalogs.items():
        note = canary if test_id == "M4B-PI-ATT-001" else "Every raw item inspected."
        assert pv_runner._run_developer_review(_review_args(
            private_root, test_id, catalog_path, commentary=note)) == 0
    assert pv_runner._finalize(SimpleNamespace(pv_run_id="pv-new",
        public_root=public_root, private_root=private_root,
        binding_manifest=private_root / "binding.json")) == 0
    public = (public_root / "pv-final.json").read_text()
    private = (private_root / "pv-final-manifest.json").read_text()
    assert json.loads(public)["pv_status"] == "Pass"
    assert canary in private and canary not in public
    assert canary not in capsys.readouterr().out
    assert all("anomaly_notes" not in path.read_text()
               for path in (public_root / "developer-status").glob("*.json"))


def test_review_rejects_arbitrary_counts_missing_rows_and_tampered_evidence(
        tmp_path, monkeypatch, pv_runner):
    _public_root, private_root, _expected, catalogs = _complete_inspection_fixture(
        tmp_path, monkeypatch, pv_runner)
    catalog_path = catalogs["M4B-PI-ATT-001"]
    args = _review_args(private_root, "M4B-PI-ATT-001", catalog_path)
    args.reviewed_field_count += 1
    with pytest.raises(pv_runner.PVError, match="COUNT_MISMATCH"):
        pv_runner._run_developer_review(args)
    args.reviewed_field_count -= 1
    catalog = json.loads(catalog_path.read_text())
    catalog["fields"].pop()
    catalog_path.write_text(json.dumps(catalog))
    with pytest.raises(pv_runner.PVError, match="CATALOG_INCOMPLETE"):
        pv_runner._run_developer_review(args)
    catalog_path.write_text(json.dumps({**catalog, "fields": [
        *catalog["fields"], {"locator": "fabricated", "type": "str", "value": "x"}]}))
    capture = private_root / "single-0" / "att-manifest.json"
    capture.write_text(capture.read_text() + " ")
    with pytest.raises(pv_runner.PVError):
        pv_runner._run_developer_review(args)


@pytest.mark.parametrize("mutation", ["catalog-row", "private-evidence", "missing-evidence",
                                      "stale-card", "wrong-tuple"])
def test_review_fails_closed_on_exact_catalog_and_evidence_mutations(
        tmp_path, monkeypatch, pv_runner, mutation):
    public_root, private_root, _expected, catalogs = _complete_inspection_fixture(
        tmp_path, monkeypatch, pv_runner)
    catalog_path = catalogs["M4B-PI-ATT-001"]
    args = _review_args(private_root, "M4B-PI-ATT-001", catalog_path)
    if mutation in {"catalog-row", "wrong-tuple"}:
        value = json.loads(catalog_path.read_text())
        if mutation == "catalog-row":
            value["rows"].pop()
        else:
            value["expected_tuple"] = {"content_sha256": "b" * 64}
        catalog_path.write_text(json.dumps(value))
    elif mutation == "stale-card":
        card_path = public_root / "single-0/result.json"
        card_path.write_text(card_path.read_text() + " ")
    else:
        evidence = private_root / "single-0/att-manifest.json"
        if mutation == "private-evidence":
            evidence.write_text(evidence.read_text() + " ")
        else:
            evidence.unlink()
    with pytest.raises(pv_runner.PVError):
        pv_runner._run_developer_review(args)
    assert not list((private_root / "developer-reviews").glob("M4B-PI-ATT-001-*.json")) if (
        private_root / "developer-reviews").exists() else True


def test_review_rejects_wrong_failed_item_and_forbidden_identity_field(
        tmp_path, monkeypatch, pv_runner):
    public_root, private_root, expected, catalogs = _complete_inspection_fixture(
        tmp_path, monkeypatch, pv_runner)
    catalog_path = catalogs["M4B-PI-ATT-001"]
    valid_locator = json.loads(catalog_path.read_text())["fields"][0]["locator"]
    pass_args = _review_args(private_root, "M4B-PI-ATT-001", catalog_path,
                             failed_item=valid_locator)
    with pytest.raises(pv_runner.PVError, match="FAILED_ITEM_INVALID"):
        pv_runner._run_developer_review(pass_args)
    fail_args = _review_args(private_root, "M4B-PI-ATT-001", catalog_path,
                             status="Fail", failed_item="NONE")
    with pytest.raises(pv_runner.PVError, match="FAILED_ITEM_INVALID"):
        pv_runner._run_developer_review(fail_args)
    assert pv_runner._run_developer_review(_review_args(
        private_root, "M4B-PI-ATT-001", catalog_path)) == 0
    card_sha = pv_runner._sha256(public_root / "single-0/result.json")
    review_path = private_root / "developer-reviews" / f"M4B-PI-ATT-001-{card_sha}.json"
    review = json.loads(review_path.read_text())
    review["reviewer_identity"] = "forbidden"
    review_path.write_text(json.dumps(review))
    with pytest.raises(pv_runner.PVError, match="REVIEW_INCOMPLETE"):
        pv_runner._load_developer_review(private_root, public_root,
            test_id="M4B-PI-ATT-001", pv_run_id="pv-new", expected=expected,
            card_path=public_root / "single-0/result.json")


def test_developer_fail_cannot_be_final_pv_pass(tmp_path, monkeypatch, pv_runner):
    public_root, private_root, _expected, catalogs = _complete_inspection_fixture(
        tmp_path, monkeypatch, pv_runner)
    for test_id, catalog_path in catalogs.items():
        locator = json.loads(catalog_path.read_text())["fields"][0]["locator"]
        args = _review_args(private_root, test_id, catalog_path,
                            status="Fail" if test_id == "M4B-PI-ATT-001" else "Pass",
                            failed_item=locator if test_id == "M4B-PI-ATT-001" else "NONE")
        pv_runner._run_developer_review(args)
    assert pv_runner._finalize(SimpleNamespace(pv_run_id="pv-new",
        public_root=public_root, private_root=private_root,
        binding_manifest=private_root / "binding.json")) == 1
    final = json.loads((public_root / "pv-final.json").read_text())
    assert final["pv_status"] == "Fail"
    assert next(row for row in final["tests"] if row["test_id"] == "M4B-PI-ATT-001")["status"] == "Fail"


def _final_args(public_root, private_root):
    return SimpleNamespace(pv_run_id="pv-new", public_root=public_root,
        private_root=private_root, binding_manifest=private_root / "binding.json")


def _designate_args(private_root, test_id, card_path, *, case_id=None):
    return SimpleNamespace(pv_run_id="pv-new", test_id=test_id,
        case_id=case_id, result_card=card_path,
        binding_manifest=private_root / "binding.json")


@pytest.mark.parametrize("script_state", ["Fail", "Incomplete", "Blocked"])
def test_g07_nonpass_script_remains_visible_despite_old_human_review(
        tmp_path, monkeypatch, pv_runner, script_state):
    public_root, private_root, _expected, catalogs = _complete_inspection_fixture(
        tmp_path, monkeypatch, pv_runner)
    for test_id, catalog_path in catalogs.items():
        assert pv_runner._run_developer_review(_review_args(
            private_root, test_id, catalog_path)) == 0
    card_path = public_root / "single-0/result.json"
    card = json.loads(card_path.read_text())
    card.update(script_status=script_state, status=script_state,
                error_code=f"SCRIPT_{script_state.upper()}")
    card_path.write_text(json.dumps(card))
    assert pv_runner._finalize(_final_args(public_root, private_root)) == 1
    final = json.loads((public_root / "pv-final.json").read_text())
    item = next(row for row in final["tests"] if row["test_id"] == "M4B-PI-ATT-001")
    assert item["script_status"] == script_state and item["status"] == script_state
    assert f"SCRIPT_{script_state.upper()}" in item["reason_codes"]
    assert final["pv_status"] == script_state


@pytest.mark.parametrize("mutation,expected_state", [
    ("user-fail", "Fail"), ("user-pending", "NeedsHumanReview"),
    ("developer-missing", "NeedsDeveloperReview"),
    ("review-stale", "Incomplete"),
    ("wrong-tuple", "Incomplete")])
def test_g10_finalizer_reports_each_nonpass_layer(
        tmp_path, monkeypatch, pv_runner, mutation, expected_state):
    public_root, private_root, _expected, catalogs = _complete_inspection_fixture(
        tmp_path, monkeypatch, pv_runner)
    for test_id, catalog_path in catalogs.items():
        if mutation == "developer-missing" and test_id == "M4B-PI-ATT-001":
            continue
        assert pv_runner._run_developer_review(_review_args(
            private_root, test_id, catalog_path)) == 0
    if mutation.startswith("user-"):
        card_path = public_root / "semantic-attempt-0/result.json"
        if mutation == "user-fail":
            card = json.loads(card_path.read_text())
            card.update(user_verdict="Fail", status="Fail")
            card_path.write_text(json.dumps(card))
        else:
            card_path.unlink()
    elif mutation == "review-stale":
        card_path = public_root / "single-0/result.json"
        assert pv_runner._run_designate_result(_designate_args(
            private_root, "M4B-PI-ATT-001", card_path)) == 0
        card_path.write_text(card_path.read_text() + " ")
    elif mutation == "wrong-tuple":
        card_path = public_root / "single-0/result.json"
        card = json.loads(card_path.read_text())
        card["expected_tuple"] = {"content_sha256": "b" * 64}
        card_path.write_text(json.dumps(card))
    assert pv_runner._finalize(_final_args(public_root, private_root)) == 1
    final = json.loads((public_root / "pv-final.json").read_text())
    test_id = "M4B-PI-SEM-001" if mutation.startswith("user-") else "M4B-PI-ATT-001"
    item = next(row for row in final["tests"] if row["test_id"] == test_id)
    assert item["status"] == expected_state and final["pv_status"] == expected_state
    assert item["reason_codes"]


def test_g09_semantic_replacement_preserves_siblings_and_invalidates_old_user_pass(
        tmp_path, monkeypatch, pv_runner):
    public_root, private_root, expected, catalogs = _complete_inspection_fixture(
        tmp_path, monkeypatch, pv_runner)
    for test_id, catalog_path in catalogs.items():
        assert pv_runner._run_developer_review(_review_args(
            private_root, test_id, catalog_path)) == 0
    assert pv_runner._finalize(_final_args(public_root, private_root)) == 0
    new_path = _write_semantic_verdict(public_root, private_root, pv_runner,
        case_id="S01-IDENTITY", attempt="semantic-new-0", expected=expected,
        verdict="Fail")
    assert pv_runner._run_designate_result(_designate_args(private_root,
        "M4B-PI-SEM-001", new_path, case_id="S01-IDENTITY")) == 0
    assert pv_runner._finalize(_final_args(public_root, private_root)) == 1
    old = json.loads((public_root / "pv-final.json").read_text())
    current = json.loads((public_root / "pv-final-0002.json").read_text())
    assert old["pv_status"] == "Pass" and current["pv_status"] == "Fail"
    cases = next(row for row in current["tests"] if row["test_id"] == "M4B-PI-SEM-001")["cases"]
    assert cases[0]["card_sha256"] == pv_runner._sha256(new_path)
    assert cases[1:] == next(row for row in old["tests"] if row["test_id"] == "M4B-PI-SEM-001")["cases"][1:]


@pytest.mark.parametrize("test_id,suffix", [
    ("M4B-PI-WAKE-001", "wake"), ("M4B-PI-RES-001", "res")])
def test_g09_case_replacement_invalidates_old_aggregate_review(
        tmp_path, monkeypatch, pv_runner, test_id, suffix):
    public_root, private_root, expected, catalogs = _complete_inspection_fixture(
        tmp_path, monkeypatch, pv_runner)
    for item, catalog_path in catalogs.items():
        assert pv_runner._run_developer_review(_review_args(
            private_root, item, catalog_path)) == 0
    old_aggregate = public_root / f"aggregate-{suffix}/result.json"
    old_case = json.loads(old_aggregate.read_text())["cases"][0]
    case_id = old_case["case_id"]
    new_attempt = f"{suffix}-replacement-0"
    new_case_path = public_root / new_attempt / "result.json"
    _write_pass_card(new_case_path.parent, test_id=test_id, expected=expected,
                     case_id=case_id, attempt=new_attempt)
    _write_case_capture(private_root, test_id=test_id, case_id=case_id,
                        attempt=new_attempt, expected=expected)
    assert pv_runner._run_designate_result(_designate_args(private_root,
        test_id, new_case_path, case_id=case_id)) == 0
    new_aggregate_args = _aggregate_args(tmp_path, test_id, f"{suffix}-new")
    assert pv_runner._run_aggregate_cases(new_aggregate_args) == 0
    new_aggregate = new_aggregate_args.public_partition / "result.json"
    assert pv_runner._run_designate_result(_designate_args(
        private_root, test_id, new_aggregate)) == 0
    assert pv_runner._finalize(_final_args(public_root, private_root)) == 1
    final = json.loads((public_root / "pv-final.json").read_text())
    item = next(row for row in final["tests"] if row["test_id"] == test_id)
    assert item["status"] == "NeedsDeveloperReview"
    assert item["cases"][0]["case_attempt_id"] == new_attempt
    assert item["cases"][1:] == json.loads(old_aggregate.read_text())["cases"][1:]
