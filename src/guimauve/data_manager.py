import importlib
import shutil
from copy import deepcopy
from importlib.resources import files
from pathlib import Path

import cv2 as cv

from guimauve.models.data import Data
from guimauve.models.variant import ImageVariant


class DataManager:
    _loaded_data = {}

    @staticmethod
    def get_data(element):
        data_file = element.data_file
        if data_file in DataManager._loaded_data:
            return DataManager._loaded_data[data_file]
        data = Data.from_file(data_file)
        DataManager._loaded_data[element.data_file] = data
        return data

    @staticmethod
    def get_element(element):
        name = element.name
        data_file = element.data_file
        data = DataManager.get_data(element)

        if data.elements is None:
            data.elements = {}

        if not element._is_new:
            element = data.elements.get(name)
        element.name = name
        element.data_file = data_file

        for variant in element.variants or []:
            if isinstance(variant, ImageVariant):
                variant.path = str(Path(data.image_dir) / variant.path)
                image = cv.imread(variant.path)
                variant.image = cv.cvtColor(image, cv.COLOR_BGR2RGB)

        return element

    @staticmethod
    def save_element(element):
        data = DataManager.get_data(element)
        element = deepcopy(element)
        name = element.name
        data_file = element.data_file

        element.name = None
        element.data_file = None

        for variant in element.variants or []:
            if isinstance(variant, ImageVariant):
                cv.imwrite(variant.path, cv.cvtColor(variant.image, cv.COLOR_RGB2BGR))
                variant.path = str(Path(variant.path).relative_to(data.image_dir))
                variant.image = None

        if data.elements is None:
            data.elements = {}

        module = importlib.import_module(f"guimauve.data.{data.module}")
        setattr(module.Elements, name, element)

        data.elements[name] = element
        data.to_file(data_file)
        DataManager.build_module(data_file, data)

    @staticmethod
    def get_modules_root() -> Path:
        return Path(str(files("guimauve") / "data"))

    @staticmethod
    def build_module(file, data):
        if data.module is None:
            return

        data = deepcopy(data)

        parts = data.module.split(".")
        parts[-1] += ".py"
        path = DataManager.get_modules_root()
        path = Path(path, *parts)
        path.parent.mkdir(parents=True, exist_ok=True)

        imports = [
            "from guimauve.metaclass.metadata import MetaData",
            "from guimauve.models.element import Element",
            "from guimauve.models.replay import Replay",
        ]

        constants = [
            f'DATA_FILE = r"{Path(file)}"',
        ]

        elements = ["class Elements(metaclass=MetaData, model=Element, data_file=DATA_FILE):"]
        if data.elements:
            for name, element in data.elements.items():
                element.name = name
                elements.append(f"    {name} = Element.from_dict({element.to_dict()})")
        else:
            elements.append("    pass")

        replays = ["class Replays(metaclass=MetaData, model=Replay, data_file=DATA_FILE):"]
        if data.replays:
            for name, replay in data.replays.items():
                replay_dict = replay.to_dict()
                replay_dict["name"] = name
                if "script" in replay_dict:
                    replay_dict["script"] = str(Path(data.replay_dir, replay.script))
                replays.append(f"    {replay.name} = Replay.from_dict({replay_dict})")
        else:
            replays.append("    pass")

        with path.open(mode="w+", encoding="utf-8") as f:
            f.write("\n".join(imports))
            f.write("\n\n")
            f.write("\n".join(constants))
            f.write("\n\n\n")
            f.write("\n".join(elements))
            f.write("\n\n\n")
            f.write("\n".join(replays))
            f.write("\n")

    @staticmethod
    def list_modules():
        root = DataManager.get_modules_root()
        if not root.exists():
            return []

        result = []
        for py_file in sorted(root.rglob("*.py")):
            source_path = ""
            with py_file.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("DATA_FILE ="):
                        source_path = line.split('"', 2)[1]
                        break

            rel_path = py_file.relative_to(root)
            module_name = ".".join(rel_path.with_suffix("").parts)

            result.append({"name": module_name, "source": source_path})

        return result

    @staticmethod
    def purge_modules():
        root = DataManager.get_modules_root()
        if not root.exists():
            return 0

        purged = []
        for py_file in root.rglob("*.py"):
            try:
                py_file.unlink()
                rel_path = py_file.relative_to(root)
                module_name = ".".join(rel_path.with_suffix("").parts)
                purged.append(module_name)
            except Exception as e:
                print(f"[ERR] Could not delete {module_name}: {e}")

        DataManager._cleanup_empty_dirs()

        return purged

    @staticmethod
    def delete_module(module_name):
        root = DataManager.get_modules_root()

        parts = module_name.split(".")
        target_file = root.joinpath(*parts).with_suffix(".py")

        if target_file.exists() and target_file.is_file():
            try:
                target_file.unlink()
                DataManager._cleanup_empty_dirs()
                return True
            except Exception as e:
                print(f"[ERROR] Failed to delete module {module_name}: {e}")
                return False

        return False

    @staticmethod
    def _cleanup_empty_dirs():
        root = DataManager.get_modules_root()
        if not root.exists():
            return

        for folder in sorted(root.glob("**/"), key=lambda p: len(p.parts), reverse=True):
            if folder == root or not folder.is_dir():
                continue

            if not any(folder.rglob("*.py")):
                try:
                    shutil.rmtree(folder)
                except OSError as e:
                    print(f"[WARNING] Could not remove folder {folder}: {e}")
