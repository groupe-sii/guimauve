import argparse
import importlib
import sys
from pathlib import Path

import yaml

from guimauve.data_manager import DataManager
from guimauve.drivers.local.driver import LocalDriver
from guimauve.drivers.vnc.driver import VNCDriver
from guimauve.models.base import ModelValidationError
from guimauve.models.data import Data
from guimauve.models.parameters.parameters import DefaultParams, Parameters


def check_data_path(value):
    path = Path(value)
    if not path.exists():
        raise argparse.ArgumentTypeError(f"The path '{value}' does not exist.")
    if path.is_file():
        if path.suffix not in (".json", ".yml", ".yaml"):
            raise argparse.ArgumentTypeError(f"The file '{value}' is not a JSON or YAML file.")
        if not path.stem.endswith(".data"):
            raise argparse.ArgumentTypeError(f"The file '{value}' is not a data file")
    return path


def build(args):
    files = []
    for path in args.paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(list(path.rglob("*.data.yml")))

    if not files:
        print("[-] No .data.yml files found.")
        return 0

    max_w = max(len(str(f)) for f in files)

    error_count = 0
    for file in files:
        try:
            data = Data.from_file(file)
            if errors := data.validate():
                raise ModelValidationError(errors)

            DataManager.build_module(file, data)
            print(f"[OK] {str(file):<{max_w}}  >>  {data.module}")

        except Exception as e:
            print(f"[ERR] {str(file)}  ->  {e}", file=sys.stderr)
            error_count += 1

    print(f"\n[DONE] {len(files) - error_count} modules built, {error_count} failed.")

    return 1 if error_count else 0


def list_(args):
    modules = DataManager.list_modules()

    if not modules:
        print("[-] No modules found.")
        return 0

    max_mod_len = max(len(str(module["name"])) for module in modules)
    max_idx_len = len(str(len(modules)))

    for i, module in enumerate(modules, 1):
        name = str(module["name"])
        source_ = str(module["source"])

        idx_str = f"[{i}]"
        exist = Path(source_).exists()
        print(f"{idx_str:<{max_idx_len + 2}} {name:<{max_mod_len}}  <<  {source_}{' (NOT FOUND)' if not exist else ''}")

    print(f"\n[TOTAL] {len(modules)} modules found.")

    return 0


def clean(args):
    if args.all:
        confirm = input("Are you sure you want to delete ALL built modules? [y/N] ")
        if confirm.lower() != "y":
            print("[!] Aborted.")
            return 0

        modules = DataManager.purge_modules()
        if not modules:
            print("[-] No modules found.")
            return 0

        max_w = max(len(str(m)) for m in modules)
        for module in modules:
            print(f"[OK] {str(module):<{max_w}}  (deleted)")

        print(f"\n[DONE] {len(modules)} modules deleted")

        return 0

    if args.names:
        success_count = 0
        error_count = 0
        max_w = max(len(str(n)) for n in args.names)

        for name in args.names:
            if DataManager.delete_module(name):
                print(f"[OK] {name:<{max_w}}  (deleted)")
                success_count += 1
            else:
                print(f"[ERR] {name:<{max_w}}  ->  Module not found", file=sys.stderr)
                error_count += 1

        print(f"\n[DONE] {success_count} deleted, {error_count} failed.")
        return 1 if error_count > 0 else 0

    print("[!] Error: Use --name <module_name> or --all.")
    return 1


def new(args):
    file_path = Path(args.file)
    if not file_path.suffix:
        file_path = file_path.with_suffix(".data.yml")

    if file_path.exists():
        print(f"[ERR] {file_path} already exists.", file=sys.stderr)
        return 1

    template = {"module": args.module, "image_dir": args.image_dir}

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(template, f, sort_keys=False, default_flow_style=False)

        print(f"[DONE] {file_path} (created)")
        return 0

    except Exception as e:
        print(f"[ERR] Failed to create {file_path}: {e}", file=sys.stderr)
        return 1


def edit(args):
    data = Data.from_file(args.file)
    DataManager.build_module(args.file, data)
    module = importlib.import_module(f"guimauve.data.{data.module}")
    element = DataManager.get_element(getattr(module.Elements, args.element))

    status = "updated"
    if element._is_new:
        confirm = input(f"{args.element} doesn't exist. Would you like to create it? [Y/n] ")
        if confirm.lower() != "y":
            print("[!] Aborted.")
            return
        status = "created"

    from guimauve.gui.element_editor import Context, start_element_editor

    driver = LocalDriver()

    if args.vnc:
        vnc = Parameters.from_file(args.vnc).vnc
        driver = VNCDriver(vnc.host, vnc.display, vnc.port, vnc.password)
        driver.connect()

    capture_provider = driver.capture

    element, to_save = start_element_editor(
        Context(
            element=element,
            default=DefaultParams(),
            image_dir=data.image_dir,
            capture_provider=capture_provider,
            message="",
            action="",
        )
    )

    if args.vnc:
        driver.close()

    if to_save:
        DataManager.save_element(element)
        DataManager.build_module(args.file, data)
        print(f"[DONE] {args.element} ({status})")
    else:
        print("[!] Aborted.")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    # NEW
    parser_new = subparsers.add_parser("new", help="Initialize a new data YAML")
    parser_new.add_argument("file", help="YAML file path")
    parser_new.add_argument("module", help="Module name")
    parser_new.add_argument("image_dir", help="Images directory")
    parser_new.set_defaults(func=new)

    # BUILD
    parser_build = subparsers.add_parser("build", help="Compile YAML data into Python modules")
    parser_build.add_argument("paths", nargs="+", type=check_data_path, help="YAML files or directories")
    parser_build.set_defaults(func=build)

    # LIST
    parser_list = subparsers.add_parser("list", help="List all built modules")
    parser_list.set_defaults(func=list_)

    # CLEAN
    parser_clean = subparsers.add_parser("clean")
    parser_clean.add_argument("--all", action="store_true", help="Delete everything")
    parser_clean.add_argument("names", nargs="*", help="List of module names to delete")
    parser_clean.set_defaults(func=clean)

    # EDIT
    parser_edit = subparsers.add_parser("edit", help="Edit data file using the GUI")
    parser_edit.add_argument("file", type=check_data_path, help="Path to the .data.yml file")
    parser_edit.add_argument("element", help="Name of the element to edit")
    parser_edit.add_argument("--vnc", help="Path to VNC parameter file")
    parser_edit.set_defaults(func=edit)

    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as e:
        print(f"[CRITICAL] {e}", file=sys.stderr)
        return 1
