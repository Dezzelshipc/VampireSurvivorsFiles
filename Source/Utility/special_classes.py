class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        key = cls.__name__
        if key not in cls._instances:
            cls._instances[key] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[key]


class Objectless:
    def __new__(cls, *args, **kwargs):
        raise RuntimeError('%s should not be instantiated' % cls)