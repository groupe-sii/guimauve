def bounds(model: type, field_name: str) -> tuple:
    ge = le = None
    for m in model.model_fields[field_name].metadata:
        ge = getattr(m, "ge", None) if getattr(m, "ge", None) is not None else ge
        le = getattr(m, "le", None) if getattr(m, "le", None) is not None else le
    return ge, le
