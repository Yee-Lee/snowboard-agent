"""M4-ERR WP7 content binding and bounded composition audit."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from sbd.core.candidate_identity import tracked_content_digest


EXPECTED_PUBLISHER_SITES = {
    "src/sbd/action/rest/action.py|Rest.execute.body|typed_publish",
    "src/sbd/action/speak/speaker.py|Speak.execute.body|typed_publish",
    "src/sbd/action/tool/action.py|Tool.execute.body|typed_publish",
    "src/sbd/cognition/reasoner.py|Reasoner.reason.body|legacy_publish",
    "src/sbd/cognition/reasoner.py|Reasoner._reason_product.body|typed_publish",
    "src/sbd/core/event_bus/bus.py|EventBus._dispatch_regular|typed_publish",
    "src/sbd/core/faults.py|legacy_error_event|constructor",
    "src/sbd/core/faults.py|ComponentSystemFault.to_event|constructor",
    "src/sbd/core/gpio/gpiod/driver.py|GpiodGPIO.inject_verification_fault|report_fault",
    "src/sbd/core/gpio/gpiod/driver.py|GpiodGPIO._read_ready|report_fault",
    "src/sbd/core/gpio/gpiod/driver.py|GpiodGPIO._run_callback|report_fault",
    "src/sbd/perception/listen/listener.py|Listen.perceive.body|legacy_publish",
    "src/sbd/perception/listen/listener.py|Listen.perceive.body|typed_publish",
    "src/sbd/perception/look/looker.py|Look.perceive.body|typed_publish",
    "src/sbd/perception/read/reader.py|Read.perceive.body|typed_publish",
}

EXPECTED_MAPPING_CATCHES = {
    "src/sbd/perception/listen/listener.py|Listen.perceive.body": (
        "TimeoutError", "AdapterRejected", "ComponentSystemFault", "AdapterError",
        "asyncio.CancelledError", "_AudioCaptureFailure", "Exception",
    ),
    "src/sbd/perception/listen/listener.py|Listen._capture_frames": (
        "asyncio.CancelledError", "Exception",
    ),
    "src/sbd/perception/listen/whispercpp/adapter.py|WhisperCppASRAdapter.transcribe": (
        "StopAsyncIteration", "asyncio.CancelledError", "_ASRRequestFault",
        "AdapterRejected", "(AudioProtocolError, EOFError)", "AdapterError",
    ),
    "src/sbd/cognition/reasoner.py|Reasoner._reason_product.body": (
        "asyncio.CancelledError", "Exception", "UnsupportedInputError",
        "_LocalProductFault", "_CausedProductFault", "TimeoutError",
        "asyncio.CancelledError", "Exception", "ComponentSystemFault",
        "LLMBackendError", "LLMCleanupUnprovenError", "LLMObservationError",
        "(LLMProtocolError, LLMFatalError)", "Exception", "Exception",
    ),
    "src/sbd/action/speak/speaker.py|Speak.execute.body": (
        "ComponentSystemFault", "AdapterError", "asyncio.CancelledError", "Exception",
        "asyncio.CancelledError", "Exception",
    ),
    "src/sbd/action/speak/matcha/adapter.py|MatchaTTSAdapter.synthesize.generate": (
        "asyncio.CancelledError", "_TTSRequestFault", "AdapterRejected",
        "(AudioProtocolError, EOFError)", "AdapterError",
    ),
    "src/sbd/action/rest/action.py|Rest.execute.body": ("Exception",),
    "src/sbd/action/tool/action.py|Tool.execute.body": (
        "(ToolRegistryError, ValueError, TypeError)", "asyncio.CancelledError", "Exception",
    ),
    "src/sbd/perception/read/reader.py|Read.perceive.body": (
        "ExternalMessageError", "asyncio.CancelledError", "Exception",
    ),
    "src/sbd/perception/look/looker.py|Look.perceive.body": (
        "TimeoutError", "AdapterError", "asyncio.CancelledError", "Exception",
    ),
    "src/sbd/core/event_bus/bus.py|EventBus._dispatch_regular": (
        "asyncio.CancelledError", "Exception",
    ),
    "src/sbd/core/event_bus/bus.py|EventBus._dispatch_error": (
        "asyncio.CancelledError", "Exception",
    ),
    "src/sbd/core/gpio/gpiod/driver.py|GpiodGPIO._read_ready": ("Exception",),
    "src/sbd/core/gpio/gpiod/driver.py|GpiodGPIO._run_callback": (
        "asyncio.CancelledError", "Exception",
    ),
    "src/sbd/core/display/arbiter.py|DisplayArbiter._render_current": ("Exception",),
}


def _dotted(node: ast.AST | None) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Tuple):
        return "(" + ", ".join(_dotted(item) for item in node.elts) + ")"
    return ""


class _SiteVisitor(ast.NodeVisitor):
    def __init__(self, relative: str) -> None:
        self.relative = relative
        self.scope: list[str] = []
        self.publishers: list[str] = []
        self.functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.scope.append(node.name)
        qualified = ".".join(self.scope)
        self.functions[qualified] = node
        self.generic_visit(node)
        self.scope.pop()

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def visit_Call(self, node: ast.Call) -> None:
        name = _dotted(node.func)
        kind = None
        if name == "ErrorOccurred":
            kind = "constructor"
        elif name.endswith(".publish") and node.args and isinstance(node.args[0], ast.Call):
            published = _dotted(node.args[0].func)
            if published.endswith(".to_event"):
                kind = "typed_publish"
            elif published == "legacy_error_event":
                kind = "legacy_publish"
        elif name.endswith("._report_fault"):
            kind = "report_fault"
        if kind is not None:
            self.publishers.append(
                f"{self.relative}|{'.'.join(self.scope)}|{kind}"
            )
        self.generic_visit(node)


def _constructor_violations(tree: ast.AST) -> list[str]:
    violations: list[str] = []
    required = {"where", "error", "code", "backend_disposition", "recovery_keys"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _dotted(node.func) != "ErrorOccurred":
            continue
        keywords = {keyword.arg for keyword in node.keywords}
        if node.args or None in keywords or required - keywords:
            violations.append(f"{node.lineno}:positional_or_neutral_publisher")
            continue
        disposition = next(
            keyword.value for keyword in node.keywords
            if keyword.arg == "backend_disposition"
        )
        if isinstance(disposition, ast.Constant) and disposition.value == "unclassified":
            violations.append(f"{node.lineno}:unclassified_publisher")
    return violations


def _handler_has_call(handler: ast.ExceptHandler, suffix: str) -> bool:
    return any(
        isinstance(node, ast.Call) and _dotted(node.func).endswith(suffix)
        for node in ast.walk(handler)
    )


def _catch_violations(tree: ast.AST) -> list[str]:
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    violations: list[str] = []
    typed_fault_names = {
        target.id
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        and isinstance(node.value, ast.Call)
        and _dotted(node.value.func).endswith("SystemFault.create")
        for target in (
            node.targets if isinstance(node, ast.Assign) else [node.target]
        )
        if isinstance(target, ast.Name)
    }
    for handler in (node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)):
        exception = _dotted(handler.type)
        publishes = any(
            isinstance(node, ast.Call)
            and (
                _dotted(node.func).endswith(".publish")
                or _dotted(node.func).endswith("._report_fault")
            )
            for node in ast.walk(handler)
        )
        raises = [node for node in ast.walk(handler) if isinstance(node, ast.Raise)]
        if exception == "asyncio.CancelledError":
            if publishes or not any(item.exc is None for item in raises):
                violations.append(f"{handler.lineno}:cancel_not_reraised")
            continue
        if exception not in {"Exception", "BaseException"}:
            continue

        ancestor = parents.get(handler)
        nested_in_handler = False
        while ancestor is not None:
            if isinstance(ancestor, ast.ExceptHandler):
                nested_in_handler = True
                break
            ancestor = parents.get(ancestor)
        pass_guarded_by_fault = False
        ancestor = parents.get(handler)
        while ancestor is not None:
            if isinstance(ancestor, ast.If) and "fault is not None" in ast.unparse(ancestor.test):
                pass_guarded_by_fault = True
                break
            ancestor = parents.get(ancestor)
        typed_create = any(
            isinstance(node, ast.Call)
            and _dotted(node.func).endswith("SystemFault.create")
            for node in ast.walk(handler)
        )
        bound_cause = handler.name is not None and any(
            isinstance(node, ast.Name) and node.id == handler.name
            for node in ast.walk(handler)
        )
        raises_from_bound = any(
            item.cause is not None and handler.name is not None
            and isinstance(item.cause, ast.Name) and item.cause.id == handler.name
            for item in raises
        )
        wrapped_intermediate = any(
            item.cause is not None and handler.name is not None
            and isinstance(item.cause, ast.Name) and item.cause.id == handler.name
            and isinstance(item.exc, ast.Call)
            and (
                _dotted(item.exc.func).endswith("SystemFault.create")
                or _dotted(item.exc.func) == "_AudioCaptureFailure"
            )
            for item in raises
        )
        shared_cause_names = {
            target.id
            for node in ast.walk(handler)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            and isinstance(node.value, ast.Name)
            and node.value.id == handler.name
            for target in (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
            if isinstance(target, ast.Name)
        }
        shared_typed_raise = any(
            item.cause is not None
            and isinstance(item.cause, ast.Name)
            and item.cause.id in shared_cause_names
            and item.lineno > (handler.end_lineno or handler.lineno)
            and (
                isinstance(item.exc, ast.Name) and item.exc.id in typed_fault_names
                or isinstance(item.exc, ast.Call)
                and _dotted(item.exc.func).endswith("SystemFault.create")
            )
            for item in (node for node in ast.walk(tree) if isinstance(node, ast.Raise))
        )
        explicit_failure_sink = handler.name is not None and any(
            isinstance(node, ast.Call)
            and _dotted(node.func).endswith("_HandlerFailure")
            and any(isinstance(arg, ast.Name) and arg.id == handler.name for arg in node.args)
            for node in ast.walk(handler)
        )
        valid = (
            (nested_in_handler and any(isinstance(node, ast.Pass) for node in ast.walk(handler)))
            or (pass_guarded_by_fault and any(isinstance(node, ast.Pass) for node in ast.walk(handler)))
            or any(item.exc is None for item in raises)
            or (typed_create and bound_cause)
            or shared_typed_raise
            or explicit_failure_sink
            or (_handler_has_call(handler, "._report_fault") and bound_cause)
            or (_handler_has_call(handler, "._degrade") and bound_cause)
            or (_handler_has_call(handler, "._trip_fatal") and raises_from_bound)
            or wrapped_intermediate
        )
        if not valid:
            violations.append(f"{handler.lineno}:lossy_or_suppressed_broad_catch")
    return violations


def _production_audit(root: Path) -> tuple[set[str], list[str], dict[str, tuple[str, ...]]]:
    publishers: set[str] = set()
    violations: list[str] = []
    catches: dict[str, tuple[str, ...]] = {}
    for path in sorted(root.joinpath("src/sbd").rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        visitor = _SiteVisitor(relative)
        visitor.visit(tree)
        publishers.update(visitor.publishers)
        violations.extend(f"{relative}:{item}" for item in _constructor_violations(tree))
        for qualified, function in visitor.functions.items():
            key = f"{relative}|{qualified}"
            if key in EXPECTED_MAPPING_CATCHES:
                violations.extend(
                    f"{key}:{item}" for item in _catch_violations(function)
                )
                handlers = sorted(
                    (node for node in ast.walk(function) if isinstance(node, ast.ExceptHandler)),
                    key=lambda node: node.lineno,
                )
                catches[key] = tuple(_dotted(handler.type) for handler in handlers)
    return publishers, violations, catches


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_m4_err_pu_010_tracked_content_digest(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    source = tmp_path / "src/sbd/core/value.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "src/sbd/core/value.py")

    before = tracked_content_digest(tmp_path, scopes=("src/sbd/core",))
    assert tracked_content_digest(tmp_path, scopes=("src/sbd/core",)) == before
    source.write_text("VALUE = 2\n", encoding="utf-8")
    changed = tracked_content_digest(tmp_path, scopes=("src/sbd/core",))
    assert changed != before

    untracked = tmp_path / "src/sbd/core/scratch.py"
    untracked.write_text("ignored = True\n", encoding="utf-8")
    assert tracked_content_digest(tmp_path, scopes=("src/sbd/core",)) == changed
    included = tracked_content_digest(
        tmp_path,
        scopes=("src/sbd/core",),
        pending_new_paths=("src/sbd/core/scratch.py",),
    )
    assert included != changed


def test_m4_err_pu_004_and_pi_010_closed_production_audit() -> None:
    root = Path(__file__).resolve().parents[1]
    publishers, violations, catches = _production_audit(root)
    assert publishers == EXPECTED_PUBLISHER_SITES
    assert catches == EXPECTED_MAPPING_CATCHES
    assert violations == []


@pytest.mark.parametrize(
    ("source", "reason"),
    (
        (
            "from sbd.core.events import ErrorOccurred\n"
            "event = ErrorOccurred('core.bad', 'bad')\n",
            "positional_or_neutral_publisher",
        ),
        (
            "from sbd.core.events import ErrorOccurred\n"
            "event = ErrorOccurred(where='core.bad', error='bad', code='BAD_CODE', "
            "backend_disposition='unclassified', recovery_keys=())\n",
            "unclassified_publisher",
        ),
    ),
    ids=("positional-publisher", "neutral-publisher"),
)
def test_m4_err_pu_004_negative_publishers(source: str, reason: str) -> None:
    assert any(reason in item for item in _constructor_violations(ast.parse(source)))


@pytest.mark.parametrize(
    ("source", "reason"),
    (
        (
            "def map_fault():\n"
            "    try:\n        product()\n"
            "    except Exception as exc:\n        raise RuntimeError('lost') from exc\n",
            "lossy_or_suppressed_broad_catch",
        ),
        (
            "async def map_fault(bus):\n"
            "    try:\n        await product()\n"
            "    except asyncio.CancelledError:\n"
            "        await bus.publish(ErrorOccurred('x', 'y'))\n",
            "cancel_not_reraised",
        ),
        (
            "def map_fault(logger):\n"
            "    try:\n        product()\n"
            "    except ValueError:\n        raise\n"
            "    except Exception:\n        logger.exception('suppressed')\n",
            "lossy_or_suppressed_broad_catch",
        ),
        (
            "def map_fault():\n"
            "    fault = ComponentSystemFault.create(code='BAD')\n"
            "    try:\n        product()\n"
            "    except Exception as exc:\n        saved = exc\n",
            "lossy_or_suppressed_broad_catch",
        ),
        (
            "def map_fault():\n"
            "    typed = ComponentSystemFault.create(code='BAD')\n"
            "    unrelated = RuntimeError('not typed')\n"
            "    try:\n        product()\n"
            "    except Exception as exc:\n        cause = exc\n"
            "    raise unrelated from cause\n",
            "lossy_or_suppressed_broad_catch",
        ),
    ),
    ids=(
        "lossy-broad-catch", "cancel-publish", "second-bad-catch",
        "typed-create-with-unconsumed-second-catch",
        "cause-flows-to-untyped-raise",
    ),
)
def test_m4_err_pi_010_negative_catch_sites(source: str, reason: str) -> None:
    assert any(reason in item for item in _catch_violations(ast.parse(source)))
