"""M4B composition and shared action-validator integration."""
import asyncio
from dataclasses import replace
import pytest
from sbd.cognition.llm import LLMFatalError
from sbd.cognition.prompt_builder import ListenProjector, PromptBuilder
from sbd.cognition.reasoner import Reasoner
from sbd.core.config import ConfigValueError
from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.m2_composition import M2Composition
from tests.test_m4b_cfg_001 import real_config
from tests.test_m4b_outcome_001 import ProductLLM, fact
from tests.test_m2_wrk_003 import _bus_records, _validator


class RM:
    def __init__(self): self.specs={}
    def register(self,spec): self.specs[spec.key]=spec
    def begin_recovery(self,keys): raise AssertionError("not authorized")
    async def wait_recovery(self,ticket): raise AssertionError("not authorized")
    def reasoner_capability_of(self,kind): return kind in {"listen","speak"}


class Resolver:
    def __init__(self,value): self.value=value
    def require(self,key):
        assert key=="backend.cognition.reasoner.llm"
        return self.value


def test_real_composition_injects_projector_facade_and_same_validator_P07_S06(tmp_path,monkeypatch):
    import sbd.core.m2_composition as module
    cfg=real_config(tmp_path)
    llm=ProductLLM()
    injected=[]
    sampler=object()
    def factory(config,**ports):
        injected.append(ports)
        return llm
    monkeypatch.setattr(module,"make_llm_adapter",factory)
    composition=M2Composition(llm_resource_sampler=sampler)
    rm=RM()
    bus,_,_=_bus_records()
    composition(rm,bus,cfg)
    worker=rm.specs["worker.cognition.reasoner"].factory(Resolver(llm))
    assert isinstance(worker._prompt_builder,ListenProjector)
    assert worker.control is llm.control
    assert worker._action_validator is composition.action_validator
    assert injected==[{"schedule_recovery":rm.begin_recovery,"wait_recovery":rm.wait_recovery,"resource_sampler":sampler}]
    assert "worker.perception.read" not in rm.specs and "worker.perception.look" not in rm.specs


@pytest.mark.parametrize("case",["invalid-profile","mock-sampler","real-capabilities"],ids=lambda x:"P06-P07-preflight-"+x)
def test_composition_rejects_before_factory_side_effects(tmp_path,monkeypatch,case):
    import sbd.core.m2_composition as module
    cfg=real_config(tmp_path)
    composition=M2Composition()
    if case=="invalid-profile": cfg.cognition.llm.product_profile_path.write_text("{}"); composition=M2Composition(llm_resource_sampler=object())
    elif case=="mock-sampler": cfg=DEFAULT_CONFIG; composition=M2Composition(llm_resource_sampler=object())
    elif case=="real-capabilities": cfg=replace(cfg,perception=DEFAULT_CONFIG.perception)
    calls=[]
    for name in ("make_llm_adapter","make_audio_input","make_audio_output","make_display","make_camera","make_gpio","make_asr_adapter","make_tts_adapter"):
        monkeypatch.setattr(module,name,lambda *a,**kw:calls.append(True))
    rm=RM()
    bus,_,_=_bus_records()
    with pytest.raises(ConfigValueError): composition(rm,bus,cfg)
    assert calls==[] and rm.specs=={} and composition._registered is False


def test_mock_composition_preserves_generic_projector_P06():
    rm=RM()
    bus,_,_=_bus_records()
    composition=M2Composition()
    composition(rm,bus,DEFAULT_CONFIG)
    llm=rm.specs["backend.cognition.reasoner.llm"].factory(None)
    worker=rm.specs["worker.cognition.reasoner"].factory(Resolver(llm))
    assert isinstance(worker._prompt_builder,PromptBuilder)
    assert worker._action_validator is composition.action_validator
    assert "worker.perception.read" in rm.specs and "worker.perception.look" in rm.specs


def test_action_schema_mismatch_is_e1_before_publication_S06():
    async def scenario():
        validator=_validator()
        from tests.test_state_manager import make_sm
        _,sm,*_=make_sm(action_validator=validator)
        calls=[]
        def reject(kind,payload):
            calls.append(kind)
            raise ValueError("private schema mismatch")
        validator.validate=reject
        llm=ProductLLM()
        bus,responses,errors=_bus_records()
        reasoner=Reasoner(llm,ListenProjector(),bus,{"listen","speak"}.__contains__,validator)
        with pytest.raises(LLMFatalError):
            await reasoner.reason("session",1,1,(fact(),),(),conversation_generation=1)
        assert reasoner._action_validator is validator
        assert sm._action_validator is reasoner._action_validator
        assert calls==["speak"] and responses==[] and len(errors)==1
    asyncio.run(scenario())


def test_default_real_composition_binds_all_owner_sampler_and_start_order_P07_M02(tmp_path, monkeypatch):
    import sbd.core.m2_composition as module
    from sbd.core._m4b_resource_binding import _M4BResourceBinding
    from sbd.cognition.litert_lm.resource import ProcLLMResourceSampler
    llm = ProductLLM()
    ports = {}
    def factory(config, **kwargs):
        ports.update(kwargs)
        return llm
    monkeypatch.setattr(module, "make_llm_adapter", factory)
    rm = RM()
    bus, _, _ = _bus_records()
    M2Composition()(rm, bus, real_config(tmp_path))
    sampler = ports["resource_sampler"]
    assert isinstance(sampler, ProcLLMResourceSampler)
    assert isinstance(sampler._registry, _M4BResourceBinding)
    assert sampler._registry._llm() is llm
    assert sampler._registry._asr is rm.specs["backend.perception.listen.asr"].factory(None)
    assert sampler._registry._tts is rm.specs["backend.action.speak.tts"].factory(None)
    assert set(rm.specs["backend.cognition.reasoner.llm"].dependencies) == {
        "backend.perception.listen.asr", "backend.action.speak.tts"}


def test_real_resource_manager_starts_audio_owners_before_llm_initial_sample(tmp_path, monkeypatch):
    import sbd.core.m2_composition as module
    from sbd.core.resource_manager import ResourceManager
    from sbd.core.event_bus import EventBus
    async def scenario():
        ready, order = set(), []
        make_asr, make_tts = module.make_asr_adapter, module.make_tts_adapter
        def audio_factory(original, role):
            def factory(config):
                owner = original(config)
                start = owner.start
                async def observed_start():
                    await start()
                    ready.add(role)
                    order.append(role)
                owner.start = observed_start
                return owner
            return factory
        monkeypatch.setattr(module, "make_asr_adapter", audio_factory(make_asr, "asr"))
        monkeypatch.setattr(module, "make_tts_adapter", audio_factory(make_tts, "tts"))
        class LLM(ProductLLM):
            async def start(self):
                assert ready == {"asr", "tts"}
                order.append("llm_initial_sample")
        llm = LLM()
        monkeypatch.setattr(module, "make_llm_adapter", lambda *args, **kwargs: llm)
        config, bus = real_config(tmp_path), EventBus()
        rm = ResourceManager(config, bus)
        M2Composition()(rm, bus, config)
        await rm.start()
        assert max(order.index("asr"), order.index("tts")) < order.index("llm_initial_sample")
        report = await rm.stop_all()
        assert report.failures == ()
    asyncio.run(scenario())


def _proc_stat(proc, pid, *, pgid=None, ppid=1, start=None, state="S"):
    directory = proc / str(pid)
    directory.mkdir(exist_ok=True)
    fields = [state, str(ppid), str(pid if pgid is None else pgid)] + ["0"] * 17
    fields[19] = str(pid * 10 if start is None else start)
    (directory / "stat").write_text(f"{pid} (process name) " + " ".join(fields))


def _binding_fixture(tmp_path, *, native=True):
    from types import SimpleNamespace
    from sbd.adaptor.framed_child import ChildState
    from sbd.core._m4b_resource_binding import _M4BResourceBinding
    class Owner:
        pass
    asr, tts, llm = Owner(), Owner(), Owner()
    asr._child = SimpleNamespace(pid=20, state=ChildState.READY, returncode=None)
    tts._child = SimpleNamespace(pid=30, state=ChildState.READY, returncode=None)
    llm._child = SimpleNamespace(pid=40, pgid=40)
    for pid in (10, 20, 30, 40):
        _proc_stat(tmp_path, pid)
    _proc_stat(tmp_path, 21, pgid=20, ppid=20)
    _proc_stat(tmp_path, 31, pgid=30, ppid=30)
    _proc_stat(tmp_path, 41, pgid=40, ppid=40)
    binding = _M4BResourceBinding(asr=asr, tts=tts, native_asr=native,
        native_tts=native, proc_root=tmp_path, core_pid=10)
    binding.bind_llm(llm)
    return binding, asr, tts, llm


def _owner_sample(registry, *, stamp=1, swap=0, starts=None):
    from sbd.cognition.litert_lm.resource import ProcessResource, SystemResourceSample
    roles = {}
    for role, members in registry.items():
        for pid in members:
            roles.setdefault(pid, set()).add(role)
    return SystemResourceSample(stamp, tuple(ProcessResource(pid, frozenset(owner),
        (starts or {}).get(pid, pid * 10), 10, 20, 0.0, 1)
        for pid, owner in roles.items()), 10000, 9000, swap, 0, 40.0, 0)


def test_owner_binding_counts_native_group_and_shared_mock_core_once_M02_V04(tmp_path):
    binding, asr, tts, llm = _binding_fixture(tmp_path)
    assert binding() == {"core": (10,), "vad": (20,), "asr": (21,),
                         "tts": (30, 31), "llm": (40, 41)}
    binding._native_asr = binding._native_tts = False
    sample = _owner_sample(binding())
    sample.validate()
    assert sample.processes[0].owners == frozenset({"core", "vad", "asr", "tts"})
    assert sample.combined_pss_bytes == 30


@pytest.mark.parametrize("fault", ["missing-asr", "zombie-asr", "escaped-asr", "foreign-asr",
    "audio-not-ready", "audio-exited", "llm-pgid", "pid-reuse", "group-growth"],
    ids=lambda value: "M02-owner-" + value)
def test_owner_binding_rejects_incomplete_or_changed_owner_identity(tmp_path, fault):
    from sbd.adaptor.framed_child import ChildState
    from sbd.cognition.litert_lm.resource import ResourceSampleError
    binding, asr, tts, llm = _binding_fixture(tmp_path)
    binding()
    if fault == "missing-asr": (tmp_path / "21" / "stat").unlink()
    elif fault == "zombie-asr": _proc_stat(tmp_path, 21, pgid=20, ppid=20, state="Z")
    elif fault == "escaped-asr": _proc_stat(tmp_path, 21, pgid=21, ppid=20)
    elif fault == "foreign-asr": _proc_stat(tmp_path, 21, pgid=20, ppid=1)
    elif fault == "audio-not-ready": asr._child.state = ChildState.STARTING
    elif fault == "audio-exited": tts._child.returncode = 1
    elif fault == "llm-pgid": llm._child.pgid = 10
    elif fault == "pid-reuse": _proc_stat(tmp_path, 20, start=999)
    elif fault == "group-growth": _proc_stat(tmp_path, 22, pgid=20, ppid=20)
    with pytest.raises(ResourceSampleError, match="^M4B_RESOURCE_INVALID$"):
        binding()


def _replace_audio(tmp_path, owner, old_pids, new_pid, *, destroyed=True, exited=True,
                   gone=True, ready=True):
    from types import SimpleNamespace
    from sbd.adaptor.framed_child import ChildState
    owner._child.state = ChildState.DESTROYED if destroyed else ChildState.READY
    owner._child.returncode = 0 if exited else None
    if gone:
        for pid in old_pids:
            (tmp_path / str(pid) / "stat").unlink()
    owner._child = SimpleNamespace(pid=new_pid, returncode=None,
        state=ChildState.READY if ready else ChildState.STARTING)
    _proc_stat(tmp_path, new_pid)
    _proc_stat(tmp_path, new_pid + 1, pgid=new_pid, ppid=new_pid)


@pytest.mark.parametrize("owner", ["asr", "tts"], ids=["M02-ASR-rebase", "M02-TTS-rebase"])
def test_proven_audio_replacement_rebases_only_exact_identity_preserving_health(tmp_path, owner):
    from sbd.cognition.litert_lm.resource import ResourceSampleError, ProcLLMResourceSampler
    binding, asr, tts, llm = _binding_fixture(tmp_path)
    previous = _owner_sample(binding())
    target, old = (asr, (20, 21)) if owner == "asr" else (tts, (30, 31))
    _replace_audio(tmp_path, target, old, 50)
    current = _owner_sample(binding(), stamp=2)
    with pytest.raises(ResourceSampleError): current.validate(previous)
    rebased = binding.rebase_previous(previous, current)
    current.validate(rebased)
    sampler = ProcLLMResourceSampler(ownership_registry=binding)
    sampler.validate_sample(current, previous)
    sampler.validate_sample(current, previous)  # Adapter may independently retain the old baseline.
    assert binding.rebase_previous(previous, current) == rebased
    assert replace(rebased, processes=previous.processes) == previous
    with pytest.raises(ResourceSampleError):
        replace(current, swap_used_bytes=1).validate(rebased)
    with pytest.raises(ResourceSampleError):
        replace(current, monotonic_ns=1).validate(rebased)
    tampered = replace(current, processes=tuple(replace(p, start_time_ticks=999)
        if p.pid == 10 else p for p in current.processes))
    with pytest.raises(ResourceSampleError):
        tampered.validate(binding.rebase_previous(previous, tampered))


@pytest.mark.parametrize("missing", ["destroyed", "exited", "gone", "ready"],
    ids=lambda value: "M02-rebase-proof-" + value)
def test_audio_replacement_requires_every_lifecycle_proof(tmp_path, missing):
    from sbd.cognition.litert_lm.resource import ResourceSampleError
    binding, asr, tts, llm = _binding_fixture(tmp_path)
    binding()
    _replace_audio(tmp_path, tts, (30, 31), 50, **{missing: False})
    with pytest.raises(ResourceSampleError): binding()


def test_pi_health_sources_are_bounded_and_never_fabricate_zero(monkeypatch):
    import subprocess
    from types import SimpleNamespace
    import sbd.core._m4b_resource_binding as module
    from sbd.cognition.litert_lm.resource import ResourceSampleError
    monkeypatch.setattr(module, "_read_ascii", lambda path: "42500\n")
    assert module._pi_temperature() == 42.5
    monkeypatch.setattr(module, "_read_ascii", lambda path: "unavailable")
    with pytest.raises(ResourceSampleError): module._pi_temperature()
    calls = []
    def run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(stdout=b"throttled=0x50000\n")
    monkeypatch.setattr(module.subprocess, "run", run)
    assert module._pi_throttled() == 0x50000
    assert calls[0][0] == ["/usr/bin/vcgencmd", "get_throttled"]
    assert calls[0][1]["timeout"] == 1.0
    assert calls[0][1]["check"] is True
    def timeout(*args, **kwargs): raise subprocess.TimeoutExpired("private path", 1)
    monkeypatch.setattr(module.subprocess, "run", timeout)
    with pytest.raises(ResourceSampleError) as exc: module._pi_throttled()
    import traceback
    assert "private path" not in "".join(traceback.format_exception(exc.value))


@pytest.mark.parametrize("outcome", ["generate", "r1", "r2", "notice", "silent"],
    ids=lambda value: "V01-V05-live-composition-" + value)
def test_composed_reasoner_and_actions_emit_live_outcome_and_audio_boundaries(tmp_path, monkeypatch, outcome):
    import sbd.core.m2_composition as module
    from sbd.cognition.observability import CognitionObserver
    from sbd.cognition.llm import MemoryAdmissionDenied
    from sbd.core.events import ActionCompleted
    async def scenario():
        emitted, lifecycle = [], []
        observer = CognitionObserver(sink=emitted.append)
        monkeypatch.setattr(module, "CognitionObserver", lambda: observer)
        class ObservedLLM(ProductLLM):
            async def measure(self, *args):
                snapshot = await super().measure(*args)
                self._observer.measured(snapshot)
                return snapshot
            async def generate(self, *args):
                if not isinstance(self.result, MemoryAdmissionDenied):
                    self._observer.mark("llm_send")
                result = await super().generate(*args)
                self._observer.mark("llm_terminal")
                self._observer.generated(result.metrics)
                return result
            async def observe_memory(self, point):
                lifecycle.append(point)
        result = MemoryAdmissionDenied(speak_allowed=outcome == "notice") if outcome in {"notice", "silent"} else None
        llm = ObservedLLM(result=result, revision=1 if outcome == "r2" else 0,
            counts={"current_kv_tokens": 900} if outcome == "r2" else None)
        monkeypatch.setattr(module, "make_llm_adapter", lambda *args, **kwargs: llm)
        composition, rm = M2Composition(llm_resource_sampler=object()), RM()
        bus, responses, errors = _bus_records()
        composition(rm, bus, real_config(tmp_path))
        observer.conversation_ready(1)
        observer.mark("asr_final")
        class Resources:
            def require(self, key): return rm.specs[key].factory(self)
        resources = Resources()
        reasoner = resources.require("worker.cognition.reasoner")
        await reasoner.reason("session", 1, 9, (fact("字" * 21 if outcome == "r1" else "你好"),), (),
                              conversation_generation=1)
        assert emitted == []  # Final timing waits for the actual action, not the model terminal.
        response = responses[0]
        worker = resources.require("worker.action." + response.action_kind)
        await worker.execute("session", 1, 9, response.action_payload)
        runtime = next(row for row in emitted if row["dashboard"] == "runtime")
        timing = next(row for row in emitted if row["dashboard"] == "timing")["values"]["events"]
        assert runtime["values"]["admission_result"] == {
            "generate": "GENERATE", "r1": "R1", "r2": "R2", "notice": "NOTICE", "silent": "SILENT"}[outcome]
        assert timing["asr_final"]["monotonic_ns"] is not None
        if outcome == "silent":
            assert lifecycle == ["primary_completion"]
            assert timing["tts_pcm_ready"]["monotonic_ns"] is None
        else:
            assert lifecycle == ["pre_speak", "audio_completion", "primary_completion"]
            assert timing["tts_pcm_ready"]["monotonic_ns"] is not None
        assert timing["audio_first_write"]["monotonic_ns"] is None  # Mock/null is not native ALSA.
        assert "你好" not in str(emitted) and "session" not in str(emitted)
        assert errors == []
        before = list(emitted)
        await bus.publish(ActionCompleted("rest", "ok", {}, "session", 1, 9))
        assert emitted == before  # Follow-up/duplicate rest cannot finalize the same turn twice.
        observer.begin_turn(1, 1)  # A new session can reuse the same turn counter.
        new_values = observer._values.copy()
        sampled = list(lifecycle)
        await bus.publish(ActionCompleted("rest", "ok", {}, "old-session", 1, 9))
        await bus.publish(ActionCompleted("rest", "ok", {}, "session", 1, 999))
        assert observer._values == new_values and emitted == before and lifecycle == sampled
    asyncio.run(scenario())


@pytest.mark.parametrize("fault", ["cancel", "generate-error", "observer-error"],
    ids=lambda value: "V01-V05-live-failure-" + value)
def test_reasoner_observation_failure_or_cancellation_never_publishes_normal_fact(fault):
    from sbd.cognition.observability import CognitionObserver
    async def scenario():
        rows = []
        observer = CognitionObserver(sink=rows.append)
        llm = ProductLLM(blocked=fault == "cancel",
            result=LLMFatalError("INVALID_TERMINAL") if fault != "cancel" else None)
        bus, responses, errors = _bus_records()
        reasoner = Reasoner(llm, ListenProjector(), bus, {"listen", "speak"}.__contains__,
                            _validator(), observer=observer)
        observer.conversation_ready(1)
        if fault == "observer-error":
            def failed_sink(row): raise ValueError("private observer path")
            observer._sink = failed_sink
        task = asyncio.create_task(reasoner.reason("session", 1, 9, (fact(),), (), conversation_generation=1))
        if fault == "cancel":
            await asyncio.wait_for(llm.generate_entered.wait(), 1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError): await task
            assert errors == []
        else:
            with pytest.raises(LLMFatalError): await task
            assert len(errors) == 1
        assert responses == [] and observer._values is None
        if fault != "observer-error":
            runtime = next(row for row in rows if row["dashboard"] == "runtime")
            assert runtime["values"]["admission_result"] == "E1"
            assert set(runtime["null_reasons"].values()) == {"CANCELLED" if fault == "cancel" else "FAILED"}
        assert "private observer path" not in str(errors)
    asyncio.run(scenario())


def test_rest_memory_observation_failure_reaches_sm_error_before_normal_session_exit(tmp_path, monkeypatch):
    import sbd.core.m2_composition as module
    from sbd.cognition.observability import CognitionObserver
    from sbd.core.events import ActionCompleted, StateChanged, ShutdownRequested
    from sbd.core.resource_manager.catalog import WorkerCatalog
    from sbd.core.state_manager.manager import StateManager
    from tests.test_state_manager import Worker, ConversationControl, start_perception, wait
    async def scenario():
        entered, release, error_seen = asyncio.Event(), asyncio.Event(), asyncio.Event()
        observer = CognitionObserver(sink=lambda row: None)
        monkeypatch.setattr(module, "CognitionObserver", lambda: observer)
        class FailingLLM(ProductLLM):
            async def observe_memory(self, point):
                assert point == "primary_completion"
                entered.set()
                await release.wait()
                raise LLMFatalError("MEMORY_SAMPLE_INVALID")
        llm, rm = FailingLLM(), RM()
        monkeypatch.setattr(module, "make_llm_adapter", lambda *args, **kwargs: llm)
        bus, _, errors = _bus_records()
        facts = []
        async def record_fact(event): facts.append(event)
        bus.subscribe(ActionCompleted, record_fact)
        M2Composition(llm_resource_sampler=object())(rm, bus, real_config(tmp_path))
        listen = Worker(bus, "listen", "perception", hold_after_fact=True)
        class ObservedReasoner(Worker):
            async def reason(self, session_id, turn_id, correlation_id, results, pending, *, conversation_generation):
                observer.conversation_ready(conversation_generation)
                observer.begin_turn(conversation_generation, turn_id)
                observer.outcome("SILENT")
                await super().reason(session_id, turn_id, correlation_id, results, pending,
                                     conversation_generation=conversation_generation)
        reasoner = ObservedReasoner(bus, "reasoner", "think", action_payload={})
        catalog = WorkerCatalog()
        catalog.register_perception("listen", listen)
        catalog.set_reasoner(reasoner)
        catalog.register_action("rest", rm.specs["worker.action.rest"].factory(None))
        catalog.seal()
        sm = StateManager(bus=bus, workers=catalog, wake_ack_seconds=60)
        sm._test_conversation_control = ConversationControl()
        transitions = []
        async def state_changed(event):
            transitions.append((event.new, sm._session is not None))
            if event.new == "ERROR": error_seen.set()
        bus.subscribe(StateChanged, state_changed)
        await start_perception(bus, sm, listen)
        session = sm._session
        listen.release.set()
        await wait(entered)
        await asyncio.wait_for(sm._inbox.join(), 1)
        assert sm.state == "ACTION" and sm._session is session
        assert facts == []  # Actual Rest cannot publish while its callback is pending.
        assert not error_seen.is_set() and not any(state == "IDLE" for state, _ in transitions)
        release.set()
        await wait(error_seen)
        assert ("ERROR", True) in transitions
        assert not any(state == "IDLE" for state, _ in transitions[:next(
            index for index, (state, _) in enumerate(transitions) if state == "ERROR")])
        assert errors and all(event.error == "REST_OBSERVATION_FAILED" for event in errors)
        assert facts == []  # A failed callback cannot fabricate a successful terminal Fact.
        await bus.publish(ShutdownRequested())
        await asyncio.wait_for(sm.wait_stopped(), 2)
        await sm.stop()
    asyncio.run(scenario())
