import json
import typing
import warnings
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Optional, Type, Union

import yaml
from pydantic import BaseModel, ConfigDict, PrivateAttr, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError
from pydantic_core import ErrorDetails


def _describe_enum(enum_type: Type[Enum], limit: int = 4) -> str:
    names = [member.name for member in enum_type]
    shown = ", ".join(names[:limit])
    if len(names) > limit:
        shown += ", ..."
    return f"{enum_type.__name__} enum ({shown})"


def _convert_enum_strings(value: Any, annotation: Any) -> Any:
    """Recursively convert member-name strings to enum members (through Optional/Union/list).

    Raises a clear `ValueError` on an unmatched name instead of falling through to Pydantic's
    native by-value error, which is unreadable for enums like `Key`.
    """
    origin = typing.get_origin(annotation)

    if origin is Union:
        for arg in typing.get_args(annotation):
            if arg is type(None):
                continue
            converted = _convert_enum_strings(value, arg)
            if converted is not value:
                return converted
        return value

    if origin is list and isinstance(value, list):
        args = typing.get_args(annotation)
        item_type = args[0] if args else Any
        return [_convert_enum_strings(item, item_type) for item in value]

    if isinstance(annotation, type) and issubclass(annotation, Enum) and isinstance(value, str):
        try:
            return annotation[value]
        except KeyError:
            raise ValueError(f"{value!r} is not part of the {_describe_enum(annotation)}") from None

    return value


def join_natural(items: list[str]) -> str:
    """Join quoted names as a natural-language list: 'A', 'A' and 'B', or 'A', 'B' and 'C'."""
    quoted = [f"'{item}'" for item in items]
    if len(quoted) == 1:
        return quoted[0]
    return ", ".join(quoted[:-1]) + f" and {quoted[-1]}"


def _prepare_for_dump(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {k: _prepare_for_dump(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_prepare_for_dump(v) for v in value]
    return value


def strict_only(func):
    """Skip the wrapped field/model validator unless called with `context={"strict": True}`."""

    @wraps(func)
    def wrapper(*args):
        info = args[-1]
        if not (info.context and info.context.get("strict")):
            return args[-2] if len(args) >= 2 else args[0]
        return func(*args)

    return wrapper


def raise_if_any(*issues: Optional[str]) -> None:
    """Raise one ValueError joining every non-empty issue, if any.

    Needed because multiple `@model_validator(mode="after")` on the same class stop at the
    first raise — collecting issues here lets `.validate()` surface all of them at once.
    """
    present = [issue for issue in issues if issue]
    if present:
        raise ValueError("; ".join(present))


@dataclass(frozen=True)
class Bounds:
    """Inert `Annotated[...]` metadata: a min/max Pydantic never enforces on its own.

    Read by `_check_bounds` for validation and by GUI widgets for sizing — one declaration
    driving both instead of duplicating the numbers.
    """

    min: Optional[float] = None
    max: Optional[float] = None


def _format_loc(loc: tuple) -> str:
    """Render an error `loc` tuple as a dotted/indexed path, dropping Pydantic's internal
    union-resolution tags (e.g. `function-after[...]`) that would otherwise leak into the message.
    """
    parts: list[str] = []
    for part in loc:
        if isinstance(part, int):
            if parts:
                parts[-1] += f"[{part}]"
            else:
                parts.append(f"[{part}]")
            continue

        text = str(part)
        if "[" in text and ("function-" in text or text.startswith("enum[") or text.startswith("json-")):
            continue
        parts.append(text)

    return ".".join(parts)


def _describe_error(error: ErrorDetails) -> list[str]:
    """Turn one Pydantic ErrorDetails into one or more human-readable sentences.

    Custom validators already raise a full sentence — this just strips Pydantic's "Value error, "
    prefix and splits `raise_if_any`-joined messages. Native error types get a matching template;
    anything else falls back to Pydantic's own message.
    """
    error_type = error.get("type")
    msg = error.get("msg", "")
    value = error.get("input")

    if error_type == "value_error":
        text = msg.removeprefix("Value error, ")
        return text.split("; ")
    if error_type == "missing":
        return ["is required but missing"]
    if error_type == "bool_parsing":
        return [f"{value!r} is not a valid boolean"]
    if error_type in ("model_type", "dict_type"):
        class_name = error.get("ctx", {}).get("class_name", "object")
        return [f"{value!r} is not a valid {class_name}"]
    if error_type == "string_type":
        return [f"{value!r} is not a valid string"]
    if error_type in ("int_parsing", "int_type"):
        return [f"{value!r} is not a valid integer"]
    if error_type in ("float_parsing", "float_type"):
        return [f"{value!r} is not a valid number"]

    return [msg]


def _split_field_prefix(loc: str, description: str) -> tuple:
    """Merge a leading "field_name: ..." in the description into the loc path.

    `_convert_enums_by_name` has no structural `loc` of its own, so it prefixes the field name
    in the message instead — fold it into the path here rather than showing it twice.
    """
    field, _, rest = description.partition(": ")
    if not rest or not field.replace("_", "").isalnum():
        return loc, description

    merged = f"{loc}.{field}" if loc else field
    return merged, rest


class ModelValidationError(Exception):
    def __init__(self, errors: list[ErrorDetails], context: Optional[str] = None):
        self.context = context
        self.errors = errors
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        header = f"\nValidation errors for {self.context}:" if self.context else "\nValidation errors:"
        lines = [header]
        for error in self.errors:
            loc = _format_loc(error.get("loc", ()))
            for description in _describe_error(error):
                merged_loc, description = _split_field_prefix(loc, description)
                lines.append(f"  - {merged_loc}: {description}" if merged_loc else f"  - {description}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self._build_message()


class Model(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    _overridden_fields: set = PrivateAttr(default_factory=set)
    _original_values: dict = PrivateAttr(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _convert_enums_by_name(cls, data: Any, info) -> Any:
        # Only active when loading from dict/JSON/YAML (see from_dict), never on plain
        # `Model(**kwargs)` construction — direct construction expects real enum members.
        if not isinstance(data, dict) or not (info.context and info.context.get("convert_enums")):
            return data

        converted = dict(data)
        for name, field in cls.model_fields.items():
            if name not in converted:
                continue

            # mode="before" runs on the whole raw dict, not per field, so a raised error has no
            # structural `loc` of its own — name the field directly in the message instead.
            try:
                converted[name] = _convert_enum_strings(converted[name], field.annotation)
            except ValueError as exc:
                raise ValueError(f"{name}: {exc}") from None

        return converted

    @property
    def overridden_fields(self) -> set[str]:
        return set(self._overridden_fields)

    @classmethod
    def get_bounds(cls, field_name: str) -> Optional[Bounds]:
        field = cls.model_fields[field_name]
        return next((meta for meta in field.metadata if isinstance(meta, Bounds)), None)

    @field_validator("*", mode="after")
    @classmethod
    @strict_only
    def _check_bounds(cls, v, info):
        # Field validator, not model validator: runs independently per field, so this can't be
        # swallowed by an unrelated field failing elsewhere (unlike model_validator(mode="after")).
        bounds = cls.get_bounds(info.field_name)
        if v is None or bounds is None:
            return v

        # No field name in the message: as a field validator, `loc` already carries it.
        if bounds.min is not None and v < bounds.min:
            raise ValueError(f"must be >= {bounds.min}")
        if bounds.max is not None and v > bounds.max:
            raise ValueError(f"must be <= {bounds.max}")

        return v

    def __call__(self, **kwargs) -> "Model":
        return self.model_copy(update=kwargs, deep=True)

    def update_from(self, other: "Model", overwrite: bool = True) -> "Model":
        data = {}
        # Cumulative across chained calls (default -> element -> variant): once a field is
        # overridden anywhere in the chain, its first value is kept for `without_overrides()`.
        overridden = set(self._overridden_fields)
        original = dict(self._original_values)

        for name in type(self).model_fields:
            self_val = getattr(self, name)
            other_val = getattr(other, name, None)

            if (overwrite or self_val is None) and other_val is not None:
                data[name] = other_val
                if name not in overridden:
                    original[name] = self_val
                overridden.add(name)
            else:
                data[name] = self_val

        merged = type(self)(**data)
        merged._overridden_fields = overridden
        merged._original_values = original
        return merged

    def without_overrides(self) -> "Model":
        """Return a copy with every overridden field restored to its pre-override value."""
        clean = self.model_copy(update=self._original_values, deep=True)
        clean._overridden_fields = set()
        clean._original_values = {}
        return clean

    def to_dict(self, serializable: bool = True, exclude_overridden: bool = False) -> dict:
        data = self.model_dump(mode="python")

        if exclude_overridden:
            for name in self._overridden_fields:
                if name in data:
                    data[name] = None

        return _prepare_for_dump(data) if serializable else data

    def to_json(self, exclude_overridden: bool = False, **kwargs) -> str:
        return json.dumps(self.to_dict(exclude_overridden=exclude_overridden), **kwargs)

    def to_yaml(self, exclude_overridden: bool = False, **kwargs) -> str:
        kwargs.setdefault("sort_keys", False)
        return yaml.safe_dump(self.to_dict(exclude_overridden=exclude_overridden), **kwargs)

    def to_file(self, path: Union[str, Path], exclude_overridden: bool = False, **kwargs) -> None:
        path = Path(path)
        data = self.to_dict(exclude_overridden=exclude_overridden)

        if path.suffix.lower() == ".json":
            path.write_text(json.dumps(data, **kwargs), encoding="utf-8")
        elif path.suffix.lower() in (".yml", ".yaml"):
            kwargs.setdefault("sort_keys", False)
            path.write_text(yaml.safe_dump(data, **kwargs), encoding="utf-8")
        else:
            raise ValueError(f"Unsupported file extension: {path.suffix}")

    @classmethod
    def from_dict(cls, data: dict) -> "Model":
        return cls.model_validate(data, context={"convert_enums": True})

    @classmethod
    def from_json(cls, json_str: str) -> "Model":
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "Model":
        return cls.from_dict(yaml.safe_load(yaml_str) or {})

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "Model":
        path = Path(path)

        if path.suffix.lower() == ".json":
            return cls.from_json(path.read_text(encoding="utf-8"))
        if path.suffix.lower() in (".yml", ".yaml"):
            return cls.from_yaml(path.read_text(encoding="utf-8"))
        raise ValueError(f"Unsupported file extension: {path.suffix}")

    def validate(  # type: ignore[override]
        self, raise_exception: bool = False, context: Optional[str] = None
    ) -> list[ErrorDetails]:
        # A permissively-set field may not match its declared type, which makes the serializer
        # emit a UserWarning here — noise on top of the real error `model_validate` is about to raise.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            dumped = self.model_dump(mode="python")

        try:
            type(self).model_validate(dumped, context={"strict": True})
        except PydanticValidationError as exc:
            errors = exc.errors()
            if raise_exception:
                raise ModelValidationError(errors, context=context or type(self).__name__) from exc
            return errors

        return []
