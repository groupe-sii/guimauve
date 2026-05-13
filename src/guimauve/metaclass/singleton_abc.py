import abc

from guimauve.metaclass import Singleton


class SingletonABC(Singleton, abc.ABCMeta):
    pass
