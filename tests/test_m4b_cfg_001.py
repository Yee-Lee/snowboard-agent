"""Current M4B-PROMPT P06–P08 / MEM M03–M05 strict config coverage."""
from dataclasses import replace
from pathlib import Path
import json
import pytest
from sbd.cognition.factory import make_llm_adapter
from sbd.cognition.litert_lm.lock import EXPECTED_PROFILE, profile_digest
from sbd.core.config import ConfigTypeError, ConfigValueError, UnknownConfigKey, load_config
from sbd.core.config.defaults import DEFAULT_CONFIG
from sbd.core.config.models import LLMConfig
from sbd.core.config.validate import validate_config


def release_profile():
    value = {**EXPECTED_PROFILE,"profile_stage":"release","profile_sha256":"",
             "min_mem_available_generate_bytes":2048,"min_mem_available_speak_bytes":1024,
             "measurement_evidence_locator":"test-only/synthetic"}
    value["profile_sha256"] = profile_digest(value)
    return value


def real_config(tmp_path):
    paths = []
    for name in ("python","model","profile","lock"):
        path = tmp_path/name
        path.write_text(json.dumps(release_profile()) if name == "profile" else "x")
        paths.append(path)
    cfg = replace(DEFAULT_CONFIG,
        cognition=replace(DEFAULT_CONFIG.cognition,llm=LLMConfig(driver="litert_lm",runtime_python=paths[0],model_path=paths[1],product_profile_path=paths[2],artifact_lock_path=paths[3],profile_id="core-m4b-cognition-001")),
        perception=replace(DEFAULT_CONFIG.perception,read=replace(DEFAULT_CONFIG.perception.read,enabled=False),look=replace(DEFAULT_CONFIG.perception.look,enabled=False)),
        action=replace(DEFAULT_CONFIG.action,tool=replace(DEFAULT_CONFIG.action.tool,enabled=False)),
        input_sources=replace(DEFAULT_CONFIG.input_sources,external_message=replace(DEFAULT_CONFIG.input_sources.external_message,policy=replace(DEFAULT_CONFIG.input_sources.external_message.policy,enabled=False))))
    return cfg


def test_real_and_mock_capabilities_P06(tmp_path):
    cfg = real_config(tmp_path)
    validate_config(cfg)
    validate_config(DEFAULT_CONFIG)
    for section, changed in (
        ("perception",replace(cfg.perception,read=replace(cfg.perception.read,enabled=True))),
        ("perception",replace(cfg.perception,look=replace(cfg.perception.look,enabled=True))),
        ("action",replace(cfg.action,tool=replace(cfg.action.tool,enabled=True))),
        ("input_sources",DEFAULT_CONFIG.input_sources),
    ):
        with pytest.raises(ConfigValueError,match="listen-only"):
            validate_config(replace(cfg,**{section:changed}))


def test_factory_injected_ports_P07(tmp_path):
    assert type(make_llm_adapter(LLMConfig())).__name__ == "MockLLMEngineAdapter"
    cfg = real_config(tmp_path).cognition.llm
    for name in ("schedule_recovery","wait_recovery","resource_sampler"):
        with pytest.raises(ConfigValueError,match="does not accept"):
            make_llm_adapter(LLMConfig(),**{name:object()})
    with pytest.raises(ConfigValueError,match="all recovery"):
        make_llm_adapter(cfg)


@pytest.mark.parametrize("field",["runtime_python","model_path","product_profile_path","artifact_lock_path"],ids=lambda x:"P08-"+x)
@pytest.mark.parametrize("kind",["missing","relative","directory"])
def test_deployment_paths_P08(tmp_path,field,kind):
    cfg = real_config(tmp_path)
    value = {"missing":tmp_path/"absent","relative":Path("relative"),"directory":tmp_path}[kind]
    with pytest.raises(ConfigValueError):
        validate_config(replace(cfg,cognition=replace(cfg.cognition,llm=replace(cfg.cognition.llm,**{field:value}))))


@pytest.mark.parametrize("field",["child_ready_timeout_seconds","generation_timeout_seconds","terminal_grace_seconds","child_terminate_timeout_seconds","child_kill_wait_timeout_seconds"],ids=lambda x:"P08-"+x)
@pytest.mark.parametrize("value",[0,-1,float("nan"),float("inf"),False])
def test_watchdogs_P08(field,value):
    cfg = replace(DEFAULT_CONFIG,cognition=replace(DEFAULT_CONFIG.cognition,llm=replace(LLMConfig(),**{field:value})))
    with pytest.raises(ConfigTypeError if type(value) is bool else ConfigValueError):
        validate_config(cfg)
    with pytest.raises(ConfigValueError):
        make_llm_adapter(cfg.cognition.llm)


@pytest.mark.parametrize("key",["product_config_path","recycle_max_inference_attempts","recycle_owner_pss_delta_mib","recycle_min_mem_available_mib","temperature","min_mem_available_generate_bytes","prompt","grammar","schedule_recovery","resource_sampler","wait_recovery"],ids=lambda x:"M04-M05-"+x)
def test_yaml_unknown_keys(tmp_path,key):
    path=tmp_path/"config.yaml"
    path.write_text(f"cognition:\n  llm:\n    {key}: 1\n")
    with pytest.raises(UnknownConfigKey):
        load_config(local_path=path,dotenv_path=tmp_path/"none",environ={})


def test_measurement_profile_not_app_config_M03(tmp_path):
    cfg=real_config(tmp_path)
    value=release_profile()
    value.update(profile_stage="measurement",min_mem_available_generate_bytes=None,min_mem_available_speak_bytes=None,measurement_evidence_locator=None)
    value["profile_sha256"]=profile_digest(value)
    cfg.cognition.llm.product_profile_path.write_text(json.dumps(value))
    with pytest.raises(ConfigValueError,match="invalid profile"):
        validate_config(cfg)
