import shutil
from pathlib import Path


class DataWorkspace:
    DATA_FILE = "data.yml"
    IMAGES_DIR = "images"
    REPLAYS_DIR = "replays"
    IMAGE_SUFFIX = ".png"
    REPLAY_SUFFIX = ".json"

    def __init__(self, root: Path = Path(".guimauve")):
        self.root = Path(root)

    def dataset_dir(self, alias: str) -> Path:
        return self.root / alias

    def data_file(self, alias: str) -> Path:
        return self.dataset_dir(alias) / self.DATA_FILE

    def images_dir(self, alias: str) -> Path:
        return self.dataset_dir(alias) / self.IMAGES_DIR

    def replays_dir(self, alias: str) -> Path:
        return self.dataset_dir(alias) / self.REPLAYS_DIR

    def image_path(self, alias: str, element: str, variant: str) -> Path:
        return self.images_dir(alias) / element.lower() / f"{variant.lower()}{self.IMAGE_SUFFIX}"

    def replay_path(self, alias: str, name: str) -> Path:
        return self.replays_dir(alias) / f"{name.lower()}{self.REPLAY_SUFFIX}"

    def exists(self, alias: str) -> bool:
        return self.dataset_dir(alias).is_dir()

    def datasets(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return sorted(p.name for p in self.root.iterdir() if p.is_dir())

    def create_dataset(self, alias: str) -> None:
        self.images_dir(alias).mkdir(parents=True, exist_ok=True)
        self.replays_dir(alias).mkdir(parents=True, exist_ok=True)
        data_file = self.data_file(alias)
        if not data_file.exists():
            data_file.touch()

    def remove_dataset(self, alias: str) -> None:
        shutil.rmtree(self.dataset_dir(alias))
