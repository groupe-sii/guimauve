import contextvars
import copy
import json
from enum import Enum
from pathlib import Path
from typing import Optional, TypeVar, Union, get_args, get_origin

import yaml
from pydantic import BaseModel, ConfigDict, PrivateAttr, ValidationError, field_serializer, field_validator
from pydantic_core import InitErrorDetails, PydanticCustomError

Self = TypeVar("Self", bound="Model")

_STATE = ("__dict__", "__pydantic_fields_set__", "__pydantic_extra__", "__pydantic_private__")

_validate_now = contextvars.ContextVar("_validate_now", default=False)


def check_all(*checks):
    errs = []
    for check in checks:
        try:
            check()
        except PydanticCustomError as e:
            errs.append(InitErrorDetails(type=e, input=None))
    if errs:
        raise ValidationError.from_exception_data("", errs)


def _coerce_enums(ann, v, top=True):
    if v is None:
        return v
    origin = get_origin(ann)
    args = get_args(ann)
    if origin is Union:
        for a in args:
            v = _coerce_enums(a, v, top)
        return v
    if origin in (list, set, frozenset) and isinstance(v, (list, set, frozenset)):
        (inner,) = args
        return type(v)(_coerce_enums(inner, x, False) for x in v)
    if origin is dict and isinstance(v, dict):
        return {k: _coerce_enums(args[1], x, False) for k, x in v.items()}
    if isinstance(ann, type) and issubclass(ann, Enum) and isinstance(v, str):
        try:
            return ann[v]
        except KeyError:
            if top:
                raise PydanticCustomError(
                    "enum_name",
                    "Input should be a valid {enum}",
                    {"enum": ann.__name__},
                )
    return v


def _serialize_enums(v):
    if isinstance(v, Enum):
        return v.name
    if isinstance(v, (list, tuple, set, frozenset)):
        return [_serialize_enums(x) for x in v]
    if isinstance(v, dict):
        return {k: _serialize_enums(x) for k, x in v.items()}
    return v


class ModelError(ValueError):
    def __init__(self, model: str, errors: list[dict]):
        self.errors = errors

        title = f"Invalid {model} ({len(errors)} error{'s' if len(errors) > 1 else ''}):"
        lines = []
        for e in errors:
            loc = " -> ".join(map(str, e["loc"])) or "<root>"
            msg = e["msg"]
            input_ = f" (got {e['input']!r})" if e.get("input") is not None else ""
            lines.append(f"  - {loc}: {msg}{input_}")
        lines = "\n".join(lines)

        super().__init__(f"\n\n{title}\n{lines}")


class Model(BaseModel):
    model_config = ConfigDict(revalidate_instances="always")

    _overridden_fields: set = PrivateAttr(default_factory=set)
    _original_values: dict = PrivateAttr(default_factory=dict)

    def __init__(self, **data):
        if _validate_now.get():
            super().__init__(**data)
            return

        self._adopt(type(self).model_construct(**data))

    @property
    def overridden_fields(self) -> set:
        return set(self._overridden_fields)

    def to_dict(self, json_mode: bool = False) -> dict:
        return self.model_dump(mode="json" if json_mode else "python", exclude_none=True)

    def to_json(self, indent: Optional[int] = None) -> str:
        return self.model_dump_json(indent=indent, exclude_none=True)

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.model_dump(mode="json", exclude_none=True), sort_keys=False, allow_unicode=True)

    def to_file(self, path) -> None:
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix == ".json":
            path.write_text(self.to_json(indent=2))
        elif suffix in (".yaml", ".yml"):
            path.write_text(self.to_yaml())
        else:
            raise ValueError(f"Unsupported extension {suffix!r} (use .json/.yaml/.yml)")

    def resolve(self) -> list[dict]:
        private = dict(self.__pydantic_private__) if self.__pydantic_private__ else None
        token = _validate_now.set(True)
        try:
            self._adopt(type(self).model_validate(self))
            if private:
                self.__pydantic_private__.update(private)
            return []
        except ValidationError as e:
            return e.errors(include_url=False)
        finally:
            _validate_now.reset(token)

    def update(self: Self, other: BaseModel, exclude: Optional[set] = None) -> Self:
        if exclude is None:
            exclude = set()

        target = self.model_copy(deep=True)
        common = type(self).model_fields.keys() & type(other).model_fields.keys() - exclude

        for name in common:
            value = getattr(other, name)
            if value is None:
                continue
            setattr(target, name, copy.deepcopy(value))

        return target

    def without_overrides(self: Self) -> Self:
        clean = self.model_copy(update=self._original_values, deep=True)
        clean._overridden_fields = set()
        clean._original_values = {}
        return clean

    def _adopt(self, other):
        for d in _STATE:
            object.__setattr__(self, d, getattr(other, d))

    @field_validator("*", mode="before")
    @classmethod
    def _coerce_enum(cls, v, info):
        return _coerce_enums(cls.model_fields[info.field_name].annotation, v)

    @field_serializer("*", when_used="json")
    def _serialize_enum(self, v, info):
        return _serialize_enums(v)

    def __call__(self: Self, **kwargs) -> Self:
        unknown = set(kwargs) - type(self).model_fields.keys()
        if unknown:
            raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))}")

        target = self.model_copy(deep=True)
        overridden = set(self._overridden_fields)
        original = dict(self._original_values)

        for name, value in kwargs.items():
            if name not in overridden:
                original[name] = getattr(target, name)
            overridden.add(name)
            setattr(target, name, copy.deepcopy(value))

        target._overridden_fields = overridden
        target._original_values = original

        if not getattr(target, "_is_new", None) and (err := target.resolve()):
            raise ModelError(type(self).__name__, err)

        return target

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    @classmethod
    def from_json(cls, s: Union[str, bytes]):
        return cls(**json.loads(s))

    @classmethod
    def from_file(cls, path):
        path = Path(path)
        suffix = path.suffix.lower()
        text = path.read_text()
        if suffix == ".json":
            data = json.loads(text)
        elif suffix in (".yaml", ".yml"):
            data = yaml.safe_load(text)
            if data is None:
                data = {}
        else:
            raise ValueError(f"Unsupported extension {suffix!r} (use .json/.yaml/.yml)")
        return cls(**data)
