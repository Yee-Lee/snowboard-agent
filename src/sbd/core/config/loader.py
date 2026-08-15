import os
import types
import yaml
from pathlib import Path
from typing import Any, Literal, Mapping, Union, get_args, get_origin, get_type_hints
from types import MappingProxyType
import collections.abc
import dataclasses
from .models import AppConfig, SecretValue
from .defaults import DEFAULT_CONFIG
from .env import parse_dotenv, overlay_env
from .validate import (
    ConfigError, ConfigParseError, ConfigTypeError, ConfigValueError,
    UnknownConfigKey, validate_config,
)

def _get_field_type(cls, field_name: str):
    hints = get_type_hints(cls)
    return hints.get(field_name)

def _is_dataclass(cls):
    return dataclasses.is_dataclass(cls)

def _overlay_dict(
    base: Any,
    overlay: Any,
    path: str,
    field_type: Any,
    path_base: Path | None = None,
) -> Any:
    if overlay is None:
        # Check if type is Optional
        origin = get_origin(field_type)
        args = get_args(field_type)
        if type(None) in args or field_type is type(None):
            return None
        raise ConfigTypeError(f"{path} does not allow null")

    type_origin = get_origin(field_type)
    if type_origin in (Union, types.UnionType):
        errors: list[ConfigError] = []
        for candidate in (arg for arg in get_args(field_type) if arg is not type(None)):
            try:
                return _overlay_dict(base, overlay, path, candidate, path_base)
            except ConfigError as exc:
                errors.append(exc)
        if len(errors) == 1:
            raise errors[0]
        expected = " | ".join(getattr(arg, "__name__", str(arg)) for arg in get_args(field_type))
        raise ConfigTypeError(f"{path} must match {expected}") from (errors[-1] if errors else None)

    if _is_dataclass(field_type):
        if not isinstance(overlay, dict):
            raise ConfigTypeError(f"{path} must be a mapping, got {type(overlay).__name__}")

        # Optional nested config dataclasses (for example Audio native_format)
        # have no base instance when first supplied by a local config.
        if base is None:
            return _instantiate_dataclass(field_type, overlay, path, path_base)

        kwargs = {}
        for f in dataclasses.fields(field_type):
            f_val = getattr(base, f.name)
            if f.name in overlay:
                kwargs[f.name] = _overlay_dict(
                    f_val,
                    overlay[f.name],
                    f"{path}.{f.name}",
                    _get_field_type(field_type, f.name),
                    path_base,
                )
            else:
                kwargs[f.name] = f_val

        # check unknown keys
        for k in overlay:
            if not hasattr(field_type, k):
                raise UnknownConfigKey(f"{path}.{k}")

        return field_type(**kwargs)

    origin = get_origin(field_type) or field_type

    if get_origin(field_type) is Literal:
        choices = get_args(field_type)
        if not any(type(overlay) is type(choice) and overlay == choice for choice in choices):
            if path.startswith(("root.core.audio.", "root.core.display.")):
                raise ConfigValueError(
                    f"{path} must be one of {choices}, got {overlay!r}"
                )
            raise ConfigTypeError(f"{path} must be one of {choices}, got {overlay!r}")
        return overlay

    if origin is tuple:
        if not isinstance(overlay, list):
            raise ConfigTypeError(f"{path} must be a list, got {type(overlay).__name__}")
        args = get_args(field_type)
        if len(args) == 2 and args[1] is Ellipsis:
            item_type = args[0]
            return tuple(
                _overlay_dict(None, value, f"{path}[{index}]", item_type, path_base)
                for index, value in enumerate(overlay)
            )
        if args and len(args) != len(overlay):
            raise ConfigTypeError(f"{path} must contain exactly {len(args)} items")
        return tuple(
            _overlay_dict(None, value, f"{path}[{index}]", args[index], path_base)
            for index, value in enumerate(overlay)
        ) if args else tuple(overlay)

    if origin is list:
        if not isinstance(overlay, list):
            raise ConfigTypeError(f"{path} must be a list, got {type(overlay).__name__}")
        args = get_args(field_type)
        item_type = args[0] if args else Any
        return [
            _overlay_dict(None, value, f"{path}[{index}]", item_type, path_base)
            for index, value in enumerate(overlay)
        ]

    if origin is Mapping or origin is dict or origin is MappingProxyType or origin is collections.abc.Mapping:
        if not isinstance(overlay, dict):
            raise ConfigTypeError(f"{path} must be a mapping, got {type(overlay).__name__}")
        # we don't merge maps recursively, we replace? wait, for by_kind it's a mapping.
        # usually dicts in config are replaced or merged. Spec says "list替換整個default list...". Doesn't specify mapping replacement.
        # But wait, timeout_seconds.by_kind might need to be replaced.
        # Actually, let's just replace the mapping, but convert to MappingProxyType later.
        # But for GPIO pins, it's Mapping[str, GPIOPinConfig].
        args = get_args(field_type)
        key_type = args[0] if args else Any
        val_type = args[1] if args else Any

        new_dict = {}
        for k, v in overlay.items():
            decoded_key = _overlay_dict(None, k, f"{path}.<key>", key_type, path_base)
            if _is_dataclass(val_type):
                # We need a base instance to overlay on? No, if it's a map, we just instantiate.
                # Actually, there's no default for new keys in map. We can just instantiate from dict.
                # Wait, if val_type is dataclass, we must decode it.
                if not isinstance(v, dict):
                    raise ConfigTypeError(f"{path}.{k} must be a mapping")
                new_dict[decoded_key] = _instantiate_dataclass(val_type, v, f"{path}.{k}", path_base)
            else:
                new_dict[decoded_key] = _overlay_dict(None, v, f"{path}.{k}", val_type, path_base)
        return MappingProxyType(new_dict)

    if field_type is Path:
        if isinstance(overlay, str):
            value = Path(overlay)
            if path_base is not None and not value.is_absolute():
                return (path_base / value).resolve()
            return value
        raise ConfigTypeError(f"{path} must be a path string")

    if field_type is SecretValue:
        if isinstance(overlay, str):
            return SecretValue(overlay)
        raise ConfigTypeError(f"{path} must be a secret string")

    # ``bool`` is a subclass of ``int`` in Python.  Use exact types here so
    # YAML true can never silently become a numeric timeout (or vice versa).
    if origin is bool:
        if type(overlay) is not bool:
            raise ConfigTypeError(f"{path} must be bool")
    elif origin is int:
        if type(overlay) is not int:
            raise ConfigTypeError(f"{path} must be an integer")
    elif origin is float:
        if type(overlay) not in (int, float):
            raise ConfigTypeError(f"{path} must be a number")
    elif origin is str:
        if type(overlay) is not str:
            raise ConfigTypeError(f"{path} must be a string")
    elif origin is Any:
        return overlay


    return overlay

def _instantiate_dataclass(cls, data: dict, path: str, path_base: Path | None) -> Any:
    kwargs = {}
    for f in dataclasses.fields(cls):
        f_type = _get_field_type(cls, f.name)
        if f.name in data:
            if _is_dataclass(f_type):
                kwargs[f.name] = _instantiate_dataclass(f_type, data[f.name], f"{path}.{f.name}", path_base)
            else:
                kwargs[f.name] = _overlay_dict(None, data[f.name], f"{path}.{f.name}", f_type, path_base)
        else:
            if f.default is not dataclasses.MISSING:
                kwargs[f.name] = f.default
            elif f.default_factory is not dataclasses.MISSING:
                kwargs[f.name] = f.default_factory()
            else:
                raise ConfigValueError(f"Missing required field {path}.{f.name}")

    for k in data:
        if not hasattr(cls, k):
            raise UnknownConfigKey(f"{path}.{k}")

    return cls(**kwargs)

def _freeze_mappings(obj):
    if _is_dataclass(obj):
        for f in dataclasses.fields(obj):
            val = getattr(obj, f.name)
            if isinstance(val, dict):
                object.__setattr__(obj, f.name, MappingProxyType(val))
            else:
                _freeze_mappings(val)
    elif isinstance(obj, list):
        for item in obj:
            _freeze_mappings(item)

def load_config(
    *,
    local_path: Path = Path("config.local.yaml"),
    dotenv_path: Path = Path(".env"),
    environ: Mapping[str, str] = os.environ,
) -> AppConfig:

    # code defaults tree
    config = DEFAULT_CONFIG

    # load yaml
    raw_yaml = {}
    if local_path.is_file():
        with open(local_path, "r", encoding="utf-8") as f:
            try:
                raw_yaml = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                raise ConfigParseError(f"YAML parse error: {e}")

        if not isinstance(raw_yaml, dict):
            raise ConfigTypeError("YAML root must be a mapping")

    # parse dotenv and overlay env
    dotenv_vars = parse_dotenv(dotenv_path)
    # process environment takes precedence over .env
    merged_env = {**dotenv_vars, **environ}
    env_updates = overlay_env(merged_env)

    # map env updates to raw_yaml
    if "SBD_LOG_LEVEL" in env_updates:
        raw_yaml.setdefault("log", {})["level"] = env_updates["SBD_LOG_LEVEL"]
    if "SBD_MQTT_USERNAME" in env_updates:
        raw_yaml.setdefault("adaptors", {}).setdefault("mqtt", {})["username"] = env_updates["SBD_MQTT_USERNAME"]
    if "SBD_MQTT_PASSWORD" in env_updates:
        raw_yaml.setdefault("adaptors", {}).setdefault("mqtt", {})["password"] = env_updates["SBD_MQTT_PASSWORD"]

    # strict recursive merge YAML
    config = _overlay_dict(DEFAULT_CONFIG, raw_yaml, "root", AppConfig, local_path.resolve().parent)

    # validate
    validate_config(config)

    # freeze mappings
    _freeze_mappings(config)

    return config
