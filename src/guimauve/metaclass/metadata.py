from guimauve.models.model import ModelError


class MetaData(type):
    def __new__(cls, name, bases, attrs, **kwargs):
        model = kwargs.pop("model")
        alias = kwargs.pop("alias")

        cls = super().__new__(cls, name, bases, attrs, **kwargs)
        cls._model = model
        cls._alias = alias
        return cls

    def __getattribute__(cls, item):
        if item.startswith("_"):
            return super().__getattribute__(item)

        try:
            attr = super().__getattribute__(item)
        except AttributeError:
            attr = cls._model(name=item)
            attr._is_new = True
            attr._alias = cls._alias
            return attr

        if not attr._resolved:
            if errors := attr.resolve():
                raise ModelError(f"{cls._model.__name__} {item}", errors)
            attr._resolved = True

        attr._alias = cls._alias
        return attr
