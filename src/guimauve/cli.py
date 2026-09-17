import argparse
import importlib
import sys
from contextlib import contextmanager

from guimauve.models.model import ModelError
from guimauve.sync import remove_module, save_element, sync_all, sync_dataset
from guimauve.utils.naming import dataset_name_error, is_valid_entry_name
from guimauve.workspace import DataWorkspace


def main(argv=None):
    parser = argparse.ArgumentParser(prog="guimauve")
    subparsers = parser.add_subparsers(dest="command")

    _add_data_group(subparsers)

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


def _add_data_group(subparsers):
    data = subparsers.add_parser("data", help="manage data modules")
    data.set_defaults(func=lambda a: (data.print_help(), 1)[1])

    data_sub = data.add_subparsers(dest="data_command")

    p_add = data_sub.add_parser("add", help="create new dataset")
    p_add.add_argument("names", nargs="+")
    p_add.set_defaults(func=cmd_add)

    p_sync = data_sub.add_parser("sync", help="regenerate all modules from their dataset")
    p_sync.set_defaults(func=cmd_sync)

    p_edit = data_sub.add_parser("edit", help="edit an element of a dataset")
    p_edit.add_argument("name")
    p_edit.add_argument("element")
    p_edit.add_argument("--vnc", metavar="PARAMS_FILE", help="use VNC config from a params file")
    p_edit.set_defaults(func=cmd_edit)

    p_list = data_sub.add_parser("list", help="list datasets")
    p_list.set_defaults(func=cmd_list)

    p_remove = data_sub.add_parser("remove", help="delete dataset")
    p_remove.add_argument("names", nargs="+")
    p_remove.set_defaults(func=cmd_remove)


@contextmanager
def _capture_provider(vnc_file):
    if vnc_file:
        from guimauve.drivers.vnc.driver import VNCDriver
        from guimauve.models.parameters import Parameters

        params = Parameters.from_file(vnc_file)
        if errs := params.resolve():
            raise ModelError("Parameters", errs)
        if params.vnc is None:
            raise ValueError(f"No VNC configuration found in {vnc_file}")
        vnc = params.vnc
        driver = VNCDriver(vnc.host, vnc.display, vnc.port, vnc.password)
        driver.connect()
        try:
            yield driver.capture
        finally:
            driver.close()
    else:
        from guimauve.drivers.local.driver import LocalDriver

        yield LocalDriver().capture


def cmd_add(args):
    workspace = DataWorkspace()
    names = list(dict.fromkeys(args.names))

    failed = []
    for name in names:
        if reason := dataset_name_error(name):
            print(f"Invalid name: {reason}, skipped.", file=sys.stderr)
            failed.append(name)
            continue

        if workspace.exists(name):
            print(f"Dataset {name!r} already exists, skipped.", file=sys.stderr)
            continue

        workspace.create_dataset(name)
        try:
            if error := sync_dataset(workspace, name):
                print(error, file=sys.stderr)
                failed.append(name)
            else:
                print(f"Created {name!r}.")
        except OSError as e:
            print(f"Could not write module for {name!r}: {e}", file=sys.stderr)
            failed.append(name)

    return 1 if failed else 0


def cmd_sync(args):
    workspace = DataWorkspace()
    failures = sync_all(workspace)

    for alias, error in failures.items():
        print(error, file=sys.stderr)

    if failures:
        print(f"\n{len(failures)} dataset(s) failed to sync.", file=sys.stderr)
        return 1

    print("All datasets synced.")
    return 0


def cmd_edit(args):
    workspace = DataWorkspace()

    if not workspace.exists(args.name):
        print(f"Dataset {args.name!r} does not exist.", file=sys.stderr)
        return 1

    if not is_valid_entry_name(args.element):
        print(f"Invalid element name {args.element!r}: must be UPPER_SNAKE_CASE.", file=sys.stderr)
        return 1

    module = importlib.import_module(f"guimauve.data.{args.name}")
    element = getattr(module.Elements, args.element)

    status = "updated"
    if element.is_new:
        confirm = input(f"Element {args.element!r} does not exist. Create it? [y/N] ")
        if confirm.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return 0
        status = "created"

    from guimauve.gui.element_editor import Context, start_element_editor
    from guimauve.models.parameters import Parameters

    with _capture_provider(args.vnc) as capture_provider:
        element, to_save = start_element_editor(
            Context(
                element=element,
                default=Parameters().default,
                capture_provider=capture_provider,
                message="",
                action="",
            )
        )

    if not to_save:
        print("Aborted.")
        return 0

    save_element(workspace, args.name, element)
    if error := sync_dataset(workspace, args.name):
        print(error, file=sys.stderr)
        return 1

    print(f"{args.element} ({status})")
    return 0


def cmd_list(args):
    workspace = DataWorkspace()
    datasets = workspace.datasets()

    if not datasets:
        print("No datasets.")
        return 0

    for name in datasets:
        print(name)
    return 0


def cmd_remove(args):
    workspace = DataWorkspace()
    names = list(dict.fromkeys(args.names))

    missing = [n for n in names if not workspace.exists(n)]
    present = [n for n in names if workspace.exists(n)]
    for n in missing:
        print(f"Dataset {n!r} does not exist, skipped.", file=sys.stderr)

    if not present:
        return 1

    confirm = input(f"Delete {', '.join(present)} and all their data? [y/N] ")
    if confirm.strip().lower() not in ("y", "yes"):
        print("Aborted.")
        return 0

    for name in present:
        workspace.remove_dataset(name)
        remove_module(name)
        print(f"Removed {name!r}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
