# Guimauve

![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Guimauve** is a Python library for UI automation driven by computer vision. It allows for computer interaction by analyzing the screen and simulating user inputs, enabling automation on any application regardless of its underlying technology or lack of accessibility APIs.

The library bridges the gap between visual recognition and code by treating screen components as identifiable elements. It integrates image matching and Optical Character Recognition (OCR), and provides a high-level controller to simulate mouse and keyboard actions.

**Key features:**
- **Vision-Based Interaction** — Uses OpenCV (template and feature matching) and PaddleOCR to identify elements on screen, with offline-capable model downloads.
- **Multi-Screen** — Searches one, several or all monitors, with results given in desktop coordinates.
- **Flexible Execution** — Supports both **local** execution (direct control of the host machine) and **remote** execution via **VNC**, allowing automation on headless servers or virtualized environments.
- **Asset Management** — UI elements are defined in YAML files and compiled into Python modules, ensuring IDE autocompletion and type-safe access.
- **Integrated Editor** — GUI tool to capture, configure, and test elements directly from the screen during development.
- **Execution Control** — Centralized controller with timing, retries, pause/resume, and an interactive debug mode to resolve detection failures at runtime.

---

## Table of Contents

**Setup**
- [Prerequisites](#prerequisites)
- [OCR Models](#ocr-models)

**Concepts**
- [Workspace & Datasets](#workspace--datasets)
- [Elements](#elements)
  - [Coordinates](#coordinates)
  - [Target](#target)
  - [Screens](#screens)
  - [Variants](#variants)
  - [Dynamic Elements](#dynamic-elements)
  - [Overriding Parameters per Call](#overriding-parameters-per-call)
- [Data Structure (YAML)](#data-structure-yaml)

**Usage**
- [Getting Started](#getting-started)
- [Command Line Interface](#command-line-interface)

**Reference**
- [Controller](#controller)
  - [Initialization](#initialization)
  - [Mouse Methods](#mouse-methods)
  - [Keyboard Methods](#keyboard-methods)
  - [Detection Methods](#detection-methods)
  - [Screen & Session Methods](#screen--session-methods)
  - [The `sleep` parameter](#the-sleep-parameter)
- [Parameters](#parameters)
  - [VNC Settings](#vnc-settings)
  - [Screenshot Settings](#screenshot-settings)
  - [Checks](#checks)
  - [Default Parameters](#default-parameters)
- [Debug Mode](#debug-mode)

---

## Prerequisites

- OS: Windows

---

## OCR Models

Text detection/recognition — used by text variants, by image variants with `use_ocr: true`, and by `Controller.read_text`/`Controller.locate_text` — is powered by [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), with three quality tiers selectable via `OcrFidelity`:

| Fidelity | Detection model | Recognition model | Typical use |
|---|---|---|---|
| `FAST` | `PP-OCRv6_tiny_det` | `PP-OCRv6_tiny_rec` | Repeated matching in a tight loop |
| `BALANCED` | `PP-OCRv6_small_det` | `PP-OCRv6_small_rec` | Default trade-off for image variants |
| `ACCURATE` | `PP-OCRv6_medium_det` | `PP-OCRv6_medium_rec` | One-off reads where quality matters (`read_text`'s default) |

### Automatic download

Model weights are vendored under `src/guimauve/detection/paddleocr/official_models/<model_name>/` inside the installed package. The first time a given fidelity is used, if its models aren't present there yet, they are downloaded automatically (from Hugging Face) straight into that location — every run after that reuses them, with no further network access.

### Manual download (offline / air-gapped machines)

If the machine running `guimauve` has no network access, download the models you need yourself:

1. For each model, grab its files from `https://huggingface.co/PaddlePaddle/<model_name>` — e.g. [`PP-OCRv6_tiny_det`](https://huggingface.co/PaddlePaddle/PP-OCRv6_tiny_det). You need `inference.json`, `inference.pdiparams`, and `inference.yml`.
2. Place them at:
   ```
   src/guimauve/detection/paddleocr/official_models/<model_name>/inference.json
   src/guimauve/detection/paddleocr/official_models/<model_name>/inference.pdiparams
   src/guimauve/detection/paddleocr/official_models/<model_name>/inference.yml
   ```
3. Only the fidelity tier(s) you actually use are required — not all three.

If a model is missing locally and can't be downloaded, `guimauve` raises a `RuntimeError` naming the exact fidelity and expected path.

### Logging

PaddleOCR/PaddleX's own internal logging (model loading, download progress) is silenced by default so it doesn't clutter your application's logs. To restore it:

```python
from guimauve.detection.ocr import set_paddleocr_verbose

set_paddleocr_verbose(True)
```

---

## Workspace & Datasets

All definitions live in a `.guimauve/` workspace created at the root of your project. Each **dataset** is an isolated folder holding its element definitions and captured images, and maps to one generated Python module (`guimauve.data.<name>`). You never create or wire these files by hand — the CLI and the editor manage them.

```
.guimauve/
└── my_app/            # one folder per dataset
    ├── data.yml       # element definitions (safe to hand-edit, then run `sync`)
    └── images/        # screenshots, organized per element/variant (auto)
```

Dataset names are lowercase `snake_case`; element and variant names are `UPPER_SNAKE_CASE`.

---

## Elements

An `Element` defines what the controller looks for on screen and how it interacts with it. Elements are typically captured with the editor (`guimauve data edit`), stored in a dataset's `data.yml`, compiled with `guimauve data sync`, and accessed as uppercase constants in Python.

Any parameter from `DefaultProperties` can be overridden at the element level, and variants can further override a subset of those parameters. The full override chain is:

```
DefaultProperties  <  Element  <  Variant
```

### Coordinates

An element can have a fixed screen position instead of (or in addition to) image variants. When coordinates are set, detection is skipped entirely.

| Field | Type | Description |
|---|---|---|
| `x` | `int` | X coordinate relative to the top-left corner of the element's screen (the first one if `screen` is a list), never negative; with `screen=0`, relative to the primary screen, negative to the left of or above it. |
| `y` | `int` | Y coordinate relative to the top-left corner of the element's screen (the first one if `screen` is a list), never negative; with `screen=0`, relative to the primary screen, negative to the left of or above it. |
| `rel_x` | `int` | X offset relative to the current mouse position. |
| `rel_y` | `int` | Y offset relative to the current mouse position. |

`x` and `rel_x` are mutually exclusive, as are `y` and `rel_y`. An element must have at least one set of coordinates or one variant.

### Target

The `target` field defines the exact point to interact with once the element is detected.

- `[x, y]` — pixel offset within the matched bounding box.
- `"TARGET_NAME"` — refers to a named target defined inside a variant.
- If omitted, the center of the matched bounding box is used.

### Screens

The `screen` field selects the monitor(s) to search.

| Value | Description |
|---|---|
| `1` | Primary screen (default). |
| `n` | Screen `n`. Screens other than the primary one are numbered left to right, then top to bottom. |
| `0` | All screens, captured as a single image. |
| `[2, 1]` | Several screens, searched in the given order. A list must not be empty, contain `0`, or contain duplicates. |

Each variant is searched on each listed screen in order, and the search stops at the first match unless `find_all=True`, in which case matches from all screens are merged. Merged matches keep the order of the screens: those of the first screen listed come first, each screen being sorted by `match_sort` (see [Match Selection](#match-selection)). Screen `0` is a single image, so its matches are sorted across the whole desktop. `search_area` applies to each screen. A variant whose image is larger than the search area of a screen skips that screen (a warning is logged once).

Matches are returned in **desktop coordinates**: the origin is the top-left corner of the primary screen, and screens left of or above it have negative coordinates.

```python
ui.click(on=Elements.BUTTON(screen=2))        # Search screen 2 only
ui.click(on=Elements.BUTTON(screen=[2, 1]))   # Screen 2 first, then the primary screen
```

> **Note:** VNC exposes a single screen. Screen numbers other than `1` are then ignored (a warning is logged once) and the whole remote screen is used.

### Variants

Each element can have one or more variants, declared as a list. Every variant has an uppercase `name` (e.g. `DEFAULT`, `DARK_THEME`, `FRENCH`), unique within the element, and they are searched in order. The first variant with a match is used (unless `find_all=True`).

#### Image variants

Match a reference screenshot against the current screen using template or feature matching.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Uppercase identifier for the variant (e.g. `DEFAULT`), unique within the element. |
| `path` | `str` | Path to the reference image file (managed by the editor). |
| `targets` | `list` | Named click targets, each defined as `{name, x, y}` offsets within the image. |
| `default_target` | `str` | Name of the target used when no `target` is specified at the element level. |
| `match_area` | `Area` | Crops the reference image before matching, to exclude irrelevant parts of the captured template. |

Detection parameters (`use_template`, `template_confidence_threshold`, `use_feature`, `search_area`, etc.) can all be set per-variant to override element and global defaults.

#### Text variants

Match a string on screen using OCR: the text is compared with the words and lines read on screen, ignoring case, and the centre of the best match is used. Text parameters (`text_confidence_threshold`, `text_fidelity`) can be set per-variant.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Uppercase identifier for the variant (e.g. `ENGLISH`), unique within the element. |
| `text` | `str` | The text to search for, on one line. The editor saves it without leading or trailing spaces. |

### Dynamic Elements

Elements can also be instantiated directly in code without a YAML file. This is particularly useful for pure coordinate-based interactions or when building elements programmatically at runtime.

```python
from guimauve import Element

# Fixed coordinates
close_button = Element(name="CLOSE_BUTTON", x=1280, y=24)
ui.click(on=close_button)

# Relative to current mouse position
offset = Element(name="OFFSET_CLICK", rel_x=10, rel_y=5)
ui.click(on=offset)
```

Dynamic elements support the same parameters as compiled ones but are not persisted to any data file.

### Overriding Parameters per Call

Compiled elements support call syntax to produce a modified copy for a single action, without affecting the stored definition.

```python
# Use a different search area and movement speed for one specific click
ui.click(on=Elements.BUTTON(mouse_speed=500, search_area=ScreenArea.TOP))

# Force a specific timeout for this wait only
ui.wait(on=Elements.SLOW_DIALOG(timeout=15))
```

---

## Data Structure (YAML)

Each dataset stores its definitions in `.guimauve/<name>/data.yml`. Elements are declared as a mapping keyed by an uppercase name; each element's `variants` are a list of named entries. Image `path`s point into the dataset's `images/` folder and are normally written for you by the editor. Below is a full example covering all available fields.

```yaml
elements:
  LOGIN_BUTTON:
    timeout: 10
    search_area: TOP              # ScreenArea enum value
    screen: [2, 1]                # Searched on screen 2, then on the primary screen
    target: PRIMARY               # Named target defined in the variant
    variants:
      - name: DEFAULT
        path: .guimauve/my_app/images/login_button/default.png
        use_template: true
        template_confidence_threshold: 0.90
        targets:
          - name: PRIMARY
            x: 45
            y: 12

  USERNAME_FIELD:
    x: 640
    y: 360                        # Fixed coordinates, no image matching needed

  ERROR_MESSAGE:
    variants:
      - name: ENGLISH
        text: "Invalid credentials"
      - name: FRENCH
        text: "Identifiants invalides"

  NOTIFICATION_ICON:
    find_all: true
    match_sort: BOTTOM_RIGHT      # The icon nearest the bottom-right corner first
    variants:
      - name: ACTIVE
        path: .guimauve/my_app/images/notification_icon/active.png
      - name: INACTIVE
        path: .guimauve/my_app/images/notification_icon/inactive.png
```

---

## Getting Started

Since the library relies on vision, UI elements must be defined and compiled before being used in scripts. Definitions live in the `.guimauve/` workspace (see [Workspace & Datasets](#workspace--datasets)).

### 1. Create a dataset

```bash
guimauve data add my_app
```

This scaffolds `.guimauve/my_app/` and generates its (empty) Python module. Dataset names must be lowercase `snake_case`.

### 2. Define your elements

Elements are defined interactively via the **Integrated Editor** — either with the CLI (see [CLI](#command-line-interface)) or during script execution (see [Debug Mode](#debug-mode)):

```bash
guimauve data edit my_app LOGIN_BUTTON
```

The editor captures the element and saves its screenshot automatically under `.guimauve/my_app/images/`, then regenerates the module. Element names must be `UPPER_SNAKE_CASE`. You can also edit `data.yml` by hand and re-run `sync` (see next step).

### 3. Sync the modules

```bash
guimauve data sync
```

This regenerates the Python modules under `guimauve.data` from every dataset's storage, enabling autocompletion and consistent access. It runs automatically after `data edit`; run it manually whenever you modify `data.yml` by hand.

### 4. Use in your script

```python
from guimauve import Controller, Key
from guimauve.data.my_app import Elements

ui = Controller()

ui.click(on=Elements.LOGIN_BUTTON)
ui.type("admin_user", interval=0.05)
ui.press(Key.ENTER)
```

---

## Command Line Interface

All commands are grouped under `guimauve data` and operate on datasets stored in the `.guimauve/` workspace. Datasets are referenced by name, never by file path.

### `guimauve data add <names...>`

Creates one or more datasets and generates their (empty) modules.

```bash
guimauve data add my_app
guimauve data add app_a app_b   # Create several at once
```

| Argument | Description |
|---|---|
| `names` | One or more dataset names (lowercase `snake_case`). Existing datasets are skipped. |

### `guimauve data sync`

Regenerates the Python modules for every dataset from its storage. Modules whose dataset no longer exists are removed.
Each generated module records a `SOURCE_HASH` of its `data.yml`, used by the [`datasets` check](#checks) to detect outdated modules.

### `guimauve data edit <name> <element>`

Opens the Integrated Editor to create or edit an element in a dataset. Captured screenshots are saved automatically, and the dataset is re-synced on save.

```bash
guimauve data edit my_app LOGIN_BUTTON
```

| Argument / Option | Description |
|---|---|
| `name` | Target dataset. |
| `element` | Element name (`UPPER_SNAKE_CASE`). If it does not exist, you are prompted to create it. |
| `--vnc PARAMS_FILE` | Capture through a VNC session using the config from a params file, instead of the local screen. |

### `guimauve data list`

Lists all datasets in the workspace.

### `guimauve data remove <names...>`

Deletes one or more datasets and all their data (prompts for confirmation).

```bash
guimauve data remove my_app
guimauve data remove app_a app_b
```

---

## Controller

`Controller` is the main entry point for all UI interactions. It manages the driver (local or VNC), element detection, timing, and the debug editor.

### Initialization

`Controller` accepts a `Parameters` object, a dict, a path to a YAML/JSON file, or nothing (defaults to local mode).

```python
from guimauve import Controller
from guimauve import Parameters

# Default local mode
ui = Controller()

# From a Parameters object
ui = Controller(parameters=Parameters(debug_elements=True))

# From a dict
ui = Controller(parameters={"execution_mode": "vnc", "vnc": {"host": "192.168.1.10", "display": 1}})

# From a YAML/JSON file
ui = Controller(parameters="my_config.yml")
```

---

### Mouse Methods

#### `click(*, on=None, button=Button.LEFT, count=1, sleep=None)`

Moves to the element and clicks. `on` can be omitted to click at the current mouse position.

```python
ui.click(on=Elements.SUBMIT_BUTTON)
ui.click(on=Elements.ITEM, button=Button.RIGHT)
ui.click(on=Elements.ITEM, count=3)
```

#### `double_click(*, on=None, button=Button.LEFT, sleep=None)`

Shortcut for `click(..., count=2)`.

#### `triple_click(*, on=None, button=Button.LEFT, sleep=None)`

Shortcut for `click(..., count=3)`.

#### `right_click(*, on=None, sleep=None)`

Shortcut for `click(..., button=Button.RIGHT)`.

#### `move(*, on=None, sleep=None)`

Moves the mouse to the element without clicking. Respects `mouse_speed` and `mouse_direction` if set on the element.

```python
ui.move(on=Elements.MENU_ITEM)
```

#### `scroll(*, v=0, h=0, on=None, sleep=None)`

Scrolls vertically (`v`) and/or horizontally (`h`). Moves to `on` first if provided.

```python
ui.scroll(v=-3)                          # Scroll up 3 ticks
ui.scroll(v=5, on=Elements.PANEL)        # Scroll down on a specific element
ui.scroll(h=2)                           # Scroll right 2 ticks
```

#### `drag(*, on=None, button=Button.LEFT, sleep=None)`

Holds the mouse button down, moves to `on`, then releases.

```python
ui.drag(on=Elements.DROP_TARGET)
```

#### `down(*args)`

Presses and holds one or more `Key` or `Button` values.

#### `up(*args)`

Releases one or more `Key` or `Button` values.

#### `hold(*args, sleep=None)`

Context manager that holds keys or buttons for the duration of a block, then releases them.

```python
with ui.hold(Key.SHIFT):
    ui.click(on=Elements.LAST_ITEM)
```

---

### Keyboard Methods

#### `type(text, interval=0, sleep=None)`

Types a string. With `interval=0` (default), the text is pasted via clipboard for speed. With a positive `interval`, each character is typed individually with a delay in seconds between keystrokes.

```python
ui.type("hello@example.com")
ui.type("slow input", interval=0.05)
```

#### `press(*keys, interval=0, sleep=None)`

Presses a key combination. All keys are held down in order, then released in reverse, simulating a proper shortcut.

```python
ui.press(Key.ENTER)
ui.press(Key.CTRL, Key.C)
ui.press(Key.CTRL, Key.SHIFT, Key.T)
```

---

### Detection Methods

#### `locate(element=None) -> list[Match]`

Searches the element's screen(s) and returns all matches immediately, without waiting. Matches are in desktop coordinates (see [Screens](#screens)).

```python
matches = ui.locate(element=Elements.NOTIFICATION_DOT)
if matches:
    print(f"Found at {matches[0].target}")
```

#### `wait(*, on=None, off=None) -> WaitResult`

Waits for one or more elements to appear (`on`) or disappear (`off`). Both accept a single element or a list. All conditions are checked in parallel and the method returns once all are satisfied or the timeout is reached.

Returns a `WaitResult` that evaluates to `True` only if all conditions are met.

```python
# Wait for an element to appear and another to disappear simultaneously
result = ui.wait(on=Elements.SUCCESS_BANNER, off=Elements.LOADING_SPINNER)

if result:
    print("Ready")

# With lists
result = ui.wait(
    on=[Elements.CONFIRM_BUTTON, Elements.CANCEL_BUTTON],
    off=[Elements.LOADING_SPINNER]
)

# Inspect a specific element's result
elem_result = result.get("CONFIRM_BUTTON")
print(elem_result.success, elem_result.time, elem_result.match)
```

#### `scroll_until(v=0, h=0, element=None, sleep=None) -> Optional[Match]`

Scrolls in the given direction until the element is found on screen, or until the page no longer changes (end of content), checked on the screen under the mouse. Returns the first `Match` if found, otherwise `None`.

```python
match = ui.scroll_until(v=-3, element=Elements.TARGET_ROW)
```

#### `browse_menu(*elements, menu=Menu.HORIZONTAL, sleep=None)`

Navigates a multi-level menu by clicking the first element, hovering intermediate items with alternating movement directions to avoid accidental submenu closures, then clicking the last element. The following elements are searched on the screen where the first one was clicked.

```python
ui.browse_menu(Elements.FILE_MENU, Elements.EXPORT_SUBMENU, Elements.EXPORT_PDF)
```

#### `read_text(*, screen=None, screen_area=None, fidelity=OcrFidelity.ACCURATE) -> str`

Reads all text visible on a screen (or within a specific `Area`/`ScreenArea` of it) via OCR. `screen` defaults to the default screen (the first one if it is a list). Lines are returned top-to-bottom, joined by `\n`, or an empty string if nothing is detected. Defaults to the most accurate tier, since this is a one-off read rather than a tight matching loop.

```python
from guimauve import OcrFidelity

text = ui.read_text()
text = ui.read_text(screen_area=ScreenArea.TOP)
text = ui.read_text(screen=2)
text = ui.read_text(fidelity=OcrFidelity.FAST)   # trade accuracy for speed
```

#### `locate_text(text, *, screen=None, screen_area=None, fidelity=OcrFidelity.FAST, confidence_threshold=0.8) -> list[Match]`

Finds every occurrence of `text` on one or several screens (or within a specific `Area`/`ScreenArea`, applied to each screen). `screen` accepts a number or a list, as for [Screens](#screens), and defaults to the default screen(s). Text is fuzzy-matched and case-insensitive — it also matches a substring of a longer line, or a phrase spanning a few stacked lines. Unlike image variants, there is no reference size to compare against, so matches are accepted regardless of the text's rendered size. Returns a list of `Match(box, target, confidence)` in desktop coordinates, where `target` is the center of the matched text.

```python
matches = ui.locate_text("Save changes")
for match in matches:
    print(match.target, match.confidence)

matches = ui.locate_text("Save changes", screen=[1, 2])
```

---

### Screen & Session Methods

#### `screenshot(*, screen=None, screen_area=None, path=None) -> np.ndarray`

Captures a screen or a specific `Area`/`ScreenArea` of it. `screen` defaults to the default screen (the first one if it is a list); `0` captures all screens as one image. Optionally saves it to a file.

```python
img = ui.screenshot()
img = ui.screenshot(screen=2)
img = ui.screenshot(path="debug.png")
```

#### `mouse_position -> Point`

Property. Returns the current mouse coordinates as a `Point(x, y)`, in desktop coordinates.

#### `screen_size(*, screen=None) -> tuple[int, int]`

Returns the dimensions of a screen as `(width, height)`. `screen` defaults to the default screen (the first one if it is a list). Raises `ValueError` if the screen does not exist.

#### `connect()`

For VNC mode: establishes the remote session, then runs the [screen checks](#checks). Must be called before interacting if the driver requires an explicit connection.

#### `close()`

For VNC mode: closes the remote session.

---

### The `sleep` parameter

Every action method accepts an optional `sleep` keyword argument (in seconds) that overrides the global `Parameters.sleep` delay for that specific call.

```python
ui.click(on=Elements.BUTTON, sleep=1.5)   # Wait 1.5s after this click
ui.type("text", sleep=0)                  # No delay after this type
```

---

## Parameters

`Parameters` is the global configuration object passed to `Controller`. All fields have sensible defaults.

```python
from guimauve import Parameters

params = Parameters(
    debug_elements=True,
    sleep=0.3,
)
ui = Controller(parameters=params)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `execution_mode` | `"local"` \| `"vnc"` | `"local"` | Determines the driver used to control the machine. |
| `vnc` | `VNC` | `None` | VNC connection settings. Required when `execution_mode="vnc"`. |
| `debug_elements` | `bool` | `False` | If `True`, opens the Integrated Editor when an element is invalid or not found instead of raising an exception. |
| `debug_replays` | `bool` | `False` | Enables replay debugging. |
| `sleep` | `int \| float` | `0` | Global delay in seconds applied after every action. Must be positive. |
| `pause_shortcut` | `list[Key]` | `[CTRL, SHIFT, ALT]` | Key combination that pauses the controller. Press again to resume. |
| `screenshot` | `Screenshot` | see below | Automated screenshot configuration. |
| `checks` | `Checks` | see below | Optional environment checks run at startup. All disabled by default. |
| `default` | `DefaultProperties` | see below | Default parameters applied to every element at runtime. |

### VNC Settings

The `vnc` parameter accepts a `VNC` object or a dict. Either `display` or `port` must be specified.

| Field | Type | Default | Description |
|---|---|---|---|
| `host` | `str` | — | Hostname or IP address of the VNC server. |
| `display` | `int` | `None` | X display number (e.g. `1` maps to port `5901`). |
| `port` | `int` | `None` | Explicit TCP port of the VNC server. |
| `password` | `str` | `None` | VNC password. |

```python
from guimauve import VNC

params = Parameters(
    execution_mode="vnc",
    vnc=VNC(host="192.168.1.10", display=1, password="secret")
)
```

### Screenshot Settings

Controls automatic screenshots captured around actions. Useful for audit trails or debugging. The captured screen is the one of the first match for `locate`, otherwise the one under the mouse.

| Field | Type | Default | Description |
|---|---|---|---|
| `enable` | `bool` | `False` | Enables automatic screenshots. |
| `folder` | `Path \| str` | `"screenshots"` | Directory where screenshots are saved. |
| `limit` | `int` | `None` | Maximum number of screenshots to keep. |
| `on.locate` | `bool` | `True` | Capture on `locate`. |
| `on.move` | `bool` | `True` | Capture on `move`. |
| `on.click` | `bool` | `True` | Capture on `click`. |
| `on.scroll` | `bool` | `True` | Capture on `scroll`. |
| `on.type` | `bool` | `True` | Capture on `type`. |
| `on.press` | `bool` | `True` | Capture on `press`. |

```python
from guimauve.models.parameters import Screenshot, ScreenshotActions

params = Parameters(
    screenshot=Screenshot(
        enable=True,
        folder="logs/screenshots",
        limit=100,
        on=ScreenshotActions(locate=False, move=False)
    )
)
```
### Checks

Element detection relies on screenshots captured in a given environment. A different screen size or display scaling, or a generated dataset module out of date with its `data.yml`, silently breaks matching. These optional checks detect such mismatches when the controller starts, and report them all at once.

All checks are disabled by default, and each one can be enabled independently.

| Field | Type | Default | Description |
|---|---|---|---|
| `screen` | `ScreenCheck \| list[ScreenCheck]` | `None` | Screens to check. A single screen can be given without a list. |
| `datasets` | `bool \| list[str]` | `False` | `True` checks every dataset of the workspace, a list checks only the named ones. |

Each `ScreenCheck` accepts:

| Field | Type | Default | Description |
|---|---|---|---|
| `number` | `int` | `1` | Screen number, as for the element [`screen`](#screens) field. |
| `size` | `[width, height]` | `None` | Expected screen size, in physical pixels. |
| `scaling` | `int` | `None` | Expected display scaling, in percent (e.g. `125`). Windows local mode only. |

At least one of `size` or `scaling` must be set, and screen numbers must be unique.

```yaml
checks:
  screen: {size: [1920, 1080], scaling: 100}   # screen 1
  datasets: true
```

```yaml
checks:
  screen:
    - {number: 1, size: [1920, 1080], scaling: 100}
    - {number: 2, size: [1280, 720], scaling: 75}
  datasets: [my_app, login_screen]
```

```python
from guimauve import Checks, Controller, Parameters, ScreenCheck

params = Parameters(
    checks=Checks(
        screen=[ScreenCheck(number=1, size=(1920, 1080), scaling=100), ScreenCheck(number=2, size=(1280, 720))],
        datasets=True,
    )
)
ui = Controller(parameters=params)
```

**When checks run:**
- `datasets`: when the `Controller` is created.
- `screen`: when the `Controller` is created in local mode, and on [`connect()`](#connect) in VNC mode, since the remote screen is only available once connected.

**What is checked:**
- `size` is compared to `screen_size(screen=number)` (see [Screen & Session Methods](#screen--session-methods)).
- `scaling` reads the display scaling of the screen. It is skipped with a warning in VNC mode and outside Windows.
- A dataset fails if it is not found in the workspace, if its generated module is missing, unreadable or generated before `SOURCE_HASH` existed, or if its `data.yml` changed since the last [`guimauve data sync`](#guimauve-data-sync), or cannot be read.

**Results:**
- Failed checks are collected and raised together in a single `EnvironmentCheckError`, whose `failures` attribute lists each message:

  ```
  Environment checks failed (2 failures):
    - screen 1: size expected 1920x1080, got 1280x720
    - datasets: 'login' is outdated: data.yml changed since the last sync, run `guimauve data sync`
  ```

- A screen that does not exist is reported as a failure. With VNC, which exposes a single screen, screens other than `1` are skipped with a warning.
- Checks that cannot run in the current context are skipped with a warning in the logs, never raised.
- An invalid configuration (e.g. `scaling: 0`, an empty `screen` list, duplicate screen numbers, `datasets: []` or an invalid dataset name) raises a `ModelError` when the `Controller` is created.

```python
from guimauve import EnvironmentCheckError

try:
    ui = Controller(parameters="parameters.yml")
except EnvironmentCheckError as e:
    for failure in e.failures:
        print(failure)
```
---

### Default Parameters

`Parameters.default` holds the default values for all detection and interaction settings. When the controller runs an action, it applies these defaults to the element — any field already set on the element or its variants takes precedence. This means `default` acts as the fallback layer at the bottom of the override chain:

```
DefaultProperties  <  Element  <  Variant
```

```python
from guimauve.models.parameters import DefaultProperties

params = Parameters(
    default=DefaultProperties(
        timeout=10,
        template_confidence_threshold=0.90,
        use_feature=True,
    )
)
```

#### Search & Location

| Parameter | Default | Description |
|---|---|---|
| `search_area` | `ScreenArea.FULL` | Region of the screen to search. Can be a `ScreenArea` enum value or a custom `Area(top, left, bottom, right)`. |
| `timeout` | `5` | Seconds to wait for an element before raising an error (or opening the editor in debug mode). |
| `find_all` | `False` | If `True`, collects matches from all variants and screens instead of stopping at the first successful one. |
| `screen` | `1` | Screen(s) to search: a number, `0` for all screens, or a list searched in order. See [Screens](#screens). |

#### Mouse

| Parameter | Default | Description |
|---|---|---|
| `mouse_direction` | `MouseDirection.STRAIGHT` | Path the mouse takes when moving: `STRAIGHT`, `XY_X` (horizontal then vertical), or `XY_Y` (vertical then horizontal). |
| `mouse_speed` | `0` | Movement speed in pixels per second. `0` means instant (no animation). |

#### Match Selection

| Parameter | Default | Description |
|---|---|---|
| `match_index` | `0` | When multiple matches are found, which one to use (0-based). |
| `match_sort` | `MatchSort.TOP_LEFT` | How to sort matches before selecting: `CONFIDENCE` (best score first), or by position from a corner, nearest first: `TOP_LEFT`, `TOP_RIGHT`, `BOTTOM_LEFT` or `BOTTOM_RIGHT`. `XY_POSITION` is the former name of `TOP_LEFT` and is still accepted. |

#### Template Matching

| Parameter | Default | Description |
|---|---|---|
| `use_template` | `True` | Enables OpenCV template matching. |
| `template_grayscale` | `True` | Converts images to grayscale before matching (faster, recommended). |
| `template_confidence_threshold` | `0.95` | Minimum similarity score (0–1) for a match to be accepted. |

#### Feature Matching

Feature matching uses SIFT keypoints and is more robust to scale and rotation changes, but slower than template matching.

| Parameter | Default | Description |
|---|---|---|
| `use_feature` | `False` | Enables SIFT-based feature matching. |
| `feature_n_features` | `2000` | Maximum number of keypoints to detect. |
| `feature_contrast_threshold` | `0.04` | SIFT contrast threshold. Lower values detect more keypoints in low-contrast regions. |
| `feature_edge_threshold` | `10` | SIFT edge threshold. Higher values retain more edge-like keypoints. |
| `feature_sigma` | `1.6` | Gaussian blur sigma applied before keypoint detection. |
| `feature_lowe_ratio` | `0.8` | Lowe's ratio test threshold for filtering ambiguous matches. |
| `feature_min_points` | `6` | Minimum number of matching keypoints required to accept a detection. |
| `feature_ransac_threshold` | `5.0` | RANSAC reprojection threshold for homography estimation. |
| `feature_ratio_tolerance` | `0.1` | Tolerance for aspect ratio validation of detected regions. |
| `feature_size_tolerance` | `0.2` | Tolerance for size validation of detected regions. |

#### OCR (image variants)

Used when an image variant sets `use_ocr: true` — the reference image's own text is read via OCR and matched against text found on screen, useful when a UI element's exact pixels vary but its label doesn't. For matching a literal string with no reference image, use a [text variant](#text-variants), or [`locate_text`](#detection-methods) for a one-off search. See [OCR Models](#ocr-models) for the fidelity tiers and offline setup.

| Parameter | Default | Description |
|---|---|---|
| `use_ocr` | `False` | Enables PaddleOCR-based text matching for this image variant. |
| `ocr_confidence_threshold` | `0.8` | Minimum text similarity (0–1) for a match to be accepted. |
| `ocr_fidelity` | `OcrFidelity.FAST` | Which PaddleOCR model tier to use: `FAST`, `BALANCED`, or `ACCURATE`. |

#### Text (text variants)

Used to match a text variant's `text` field against text found on screen (see [Variants](#variants)).

| Parameter | Default | Description |
|---|---|---|
| `text_confidence_threshold` | `0.8` | Minimum text similarity (0–1) for a match to be accepted. |
| `text_fidelity` | `OcrFidelity.FAST` | Which PaddleOCR model tier to use: `FAST`, `BALANCED`, or `ACCURATE`. |

---

## Debug Mode

Setting `debug_elements=True` in `Parameters` activates the Integrated Editor automatically whenever:

- An element fails schema validation.
- An element cannot be found on screen within its timeout.

In each case, the editor opens with a contextual message, lets you capture or adjust the element, and then resumes script execution. If the editor is closed without saving, the action returns `None`.

This makes it possible to define and fix elements interactively, without stopping the automation script.
