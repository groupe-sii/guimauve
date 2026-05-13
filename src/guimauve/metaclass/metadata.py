class MetaData(type):
    def __new__(mcs, name, bases, attrs, **kwargs):
        model = kwargs.pop("model")
        data_file = kwargs.pop("data_file")

        cls = super().__new__(mcs, name, bases, attrs, **kwargs)
        cls._model = model
        cls._data_file = data_file
        return cls

    def __getattribute__(cls, item):
        if item.startswith("_"):
            return super().__getattribute__(item)

        try:
            attr = super().__getattribute__(item)
        except AttributeError:
            attr = cls._model(name=item)
            attr._is_new = True

        attr.data_file = cls._data_file
        return attr
