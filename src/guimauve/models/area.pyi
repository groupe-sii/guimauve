from sugar import Schema

class Area(Schema):
    top: int
    left: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        pass

    @property
    def height(self) -> int:
        pass

    @property
    def tl(self) -> tuple[int, int]:
        pass

    @property
    def tr(self) -> tuple[int, int]:
        pass

    @property
    def br(self) -> tuple[int, int]:
        pass

    @property
    def bl(self) -> tuple[int, int]:
        pass

    def __init__(self, top: int, left: int, right: int, bottom: int):
        pass

    def __call__(self, top: int, left: int, right: int, bottom: int) -> Area:
        pass
