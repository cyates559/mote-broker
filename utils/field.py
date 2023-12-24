import dataclasses


def default_factory(func, *args, **kwargs):
    return dataclasses.field(default_factory=lambda: func(*args, **kwargs))
