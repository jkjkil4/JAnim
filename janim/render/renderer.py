from abc import abstractmethod, ABCMeta


class Renderer(metaclass=ABCMeta):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialized = False

    @abstractmethod
    def init(self) -> None: ...

    @abstractmethod
    def render(self, data) -> None: ...
