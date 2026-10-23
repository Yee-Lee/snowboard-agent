"""M5T-WRK-001: actual parent adapter with a deterministic v4 child."""

import asyncio
import json
from dataclasses import replace

import pytest

from sbd.cognition.litert_lm.adapter import LiteRTLMAdapter
from sbd.cognition.litert_lm.m5_profile import M5RuntimeFacts
from sbd.cognition.litert_lm.worker import WorkerSession
from sbd.cognition.llm import LLMFatalError, ToolSemanticGeneration
from sbd.core.config.models import LLMConfig
from tests.fakes.m4b_llm_child import Sampler
from tests.test_m5t_config import TEMPLATE


class Runtime:
    protocol_version = 4

    def __init__(self):
        self.history = None
        self.sends = 0
        self.output = '{"intent":"tool","text":"","tool_name":"mock.send","arguments":{"message":"買牛奶"}}'

    def open_conversation(self):
        self.history = []

    def measure(self, text):
        current = 0 if not self.history else 100
        return {"user_tokens": 2, "current_kv_tokens": current,
                "rendered_incremental_tokens": 84,
                "runtime_prefill_tokens": 85 if current == 0 else 84,
                "output_reserve_tokens": 128, "engine_context_tokens": 1024}

    def generate(self, text):
        self.sends += 1
        self.history.append(text)
        return self.output, 8, 93 if self.sends == 1 else 192, 85 if self.sends == 1 else 84

    def scrub_ticket(self):
        pass

    def close_conversation(self):
        self.history = None


class Child:
    def __init__(self, lock, epoch):
        self.pid = self.pgid = 100 + epoch
        self.lock = lock
        self.runtime = Runtime()
        self.session = WorkerSession(self.runtime)
        self.queue = asyncio.Queue()
        self.commands = []

    async def start(self):
        return {"protocol": 4, "event": "READY", **self.lock.identity.fields,
                "pid": self.pid, "pgid": self.pgid}

    async def send(self, frame):
        self.commands.append(dict(frame))
        self.session.ledger.command(frame)
        for event in self.session.execute(frame):
            self.session.ledger.event(event)
            await self.queue.put(event)

    async def receive(self):
        return await self.queue.get()

    async def stop(self):
        assert self.runtime.history is None

    async def force_terminate(self):
        self.runtime.history = None


def make_adapter(tmp_path):
    profile = json.loads(TEMPLATE.read_text())
    profile.update(profile_stage="release", prompt_tokens=120,
        min_mem_available_generate_bytes=200,
        min_mem_available_speak_bytes=100)
    path = tmp_path / "m5-release.json"
    path.write_text(json.dumps(profile))
    lock = M5RuntimeFacts.load(path)
    children = []
    def factory(cfg, lock, epoch):
        child = Child(lock, epoch)
        children.append(child)
        return child
    async def wait_recovery(ticket):
        pass
    adapter = LiteRTLMAdapter(LLMConfig(profile_id="core-m5-tool-001"),
        lock=lock, schedule_recovery=lambda keys: None,
        wait_recovery=wait_recovery, resource_sampler=Sampler(), child_factory=factory)
    return adapter, children


@pytest.mark.asyncio
async def test_v4_adapter_measures_and_generates_without_digest_fields(tmp_path):
    adapter, children = make_adapter(tmp_path)
    await adapter.start()
    await adapter.open_conversation("s", 1)
    snapshot = await adapter.measure("s", 1, "請送出")
    assert snapshot.input_sha256 == ""
    result = await adapter.generate(snapshot, "請送出")
    assert isinstance(result, ToolSemanticGeneration)
    assert result.semantic["intent"] == "tool"
    assert adapter.conversation_revision == 1
    assert not any("input_sha256" in frame for frame in children[0].commands)
    await adapter.close_conversation("s", 1, "session_end")
    await adapter.stop()


@pytest.mark.asyncio
async def test_v4_ticket_rejects_changed_text_before_native_generate(tmp_path):
    adapter, children = make_adapter(tmp_path)
    await adapter.start()
    await adapter.open_conversation("s", 1)
    snapshot = await adapter.measure("s", 1, "請送出")
    with pytest.raises(LLMFatalError):
        await adapter.generate(snapshot, "請發出")
    assert children[0].runtime.sends == 0
    await adapter.force_abort()
