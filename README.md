# Guimauve

![Python](https://img.shields.io/badge/python-3.9+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Guimauve** is a Python library for UI automation driven by computer vision. It allows for computer interaction by analyzing the screen and simulating user inputs, enabling automation on any application regardless of its underlying technology or lack of accessibility APIs.

The library bridges the gap between visual recognition and code by treating screen components as identifiable elements. It integrates image matching and Optical Character Recognition (OCR), and provides a high-level controller to simulate mouse and keyboard actions.

**Key features:**
- **Vision-Based Interaction** — Uses OpenCV (template and feature matching) and EasyOCR to identify elements on screen.
- **Flexible Execution** — Supports both **local** execution (direct control of the host machine) and **remote** execution via **VNC**, allowing automation on headless servers or virtualized environments.
- **Asset Management** — UI elements are defined in YAML files and compiled into Python modules, ensuring IDE autocompletion and type-safe access.
- **Integrated Editor** — GUI tool to capture, configure, and test elements directly from the screen during development.
- **Execution Control** — Centralized controller with timing, retries, pause/resume, and an interactive debug mode to resolve detection failures at runtime.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Command Line Interface](#command-line-interface)
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
  - [Default Parameters](#default-parameters)
- [Elements](#elements)
  - [Coordinates](#coordinates)
  - [Target](#target)
  - [Variants](#variants)
  - [Dynamic Elements](#dynamic-elements)
  - [Overriding Parameters per Call](#overriding-parameters-per-call)
- [Data Structure (YAML)](#data-structure-yaml)
- [Roadmap](#roadmap)
- [Debug Mode](#debug-mode)

---

## Prerequisites

- OS: Windows

---

## Getting Started

Since the library relies on vision, UI elements must be defined and compiled before being used in scripts.

### 1. Initialize a data file

```bash
guimauve new my_app.data.yml my_app ./images
```

This creates a `.data.yml` file with the given module name and image directory.

### 2. Define your elements

Elements are defined either by manually editing the YAML file, or interactively via the **Integrated Editor** using commands (see [CLI](#command-line-interface)) or during script execution (see [Debug Mode](#debug-mode)).

### 3. Build the module

```bash
guimauve build my_app.data.yml
```

This compiles your YAML into a Python module under `guimauve.data`, enabling autocompletion and consistent access. **This step must be re-run every time the YAML is modified.**

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

### `guimauve new <file> <module> <image_dir>`

Initializes a new `.data.yml` file.

| Argument | Description |
|---|---|
| `file` | Path to the YAML file to create (`.data.yml` extension added if missing) |
| `module` | Python module name used in `guimauve.data.<module>` |
| `image_dir` | Directory where element screenshots will be stored |

### `guimauve build <paths...>`

Compiles one or more `.data.yml` files into Python modules. Accepts individual files or directories (scanned recursively).

```bash
guimauve build my_app.data.yml
guimauve build ./assets/
```

### `guimauve list`

Lists all currently built modules with their source file paths. Flags missing source files.

### `guimauve clean [names...] [--all]`

Deletes built modules.

```bash
guimauve clean my_app           # Delete a specific module
guimauve clean mod_a mod_b      # Delete multiple modules
guimauve clean --all            # Delete all modules (prompts for confirmation)
```

### `guimauve edit <file> <element>`

Opens the Integrated Editor to create or edit an existing element in a data file.

```bash
guimauve edit my_app.data.yml LOGIN_BUTTON
```

---

## Controller

`Controller` is the main entry point for all UI interactions. It manages the driver (local or VNC), element detection, timing, and the debug editor.

### Initialization

`Controller` accepts a `Parameters` object, a dict, a path to a YAML/JSON file, or nothing (defaults to local mode).

```python
from guimauve import Controller
from guimauve.models.parameters.parameters import Parameters

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

#### `move(*, on, sleep=None)`

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

Searches the screen for the element and returns all matches immediately, without waiting.

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

Scrolls in the given direction until the element is found on screen, or until the page no longer changes (end of content). Returns the first `Match` if found, otherwise `None`.

```python
match = ui.scroll_until(v=-3, element=Elements.TARGET_ROW)
```

#### `browse_menu(*elements, menu=Menu.HORIZONTAL, sleep=None)`

Navigates a multi-level menu by clicking the first element, hovering intermediate items with alternating movement directions to avoid accidental submenu closures, then clicking the last element.

```python
ui.browse_menu(Elements.FILE_MENU, Elements.EXPORT_SUBMENU, Elements.EXPORT_PDF)
```

---

### Screen & Session Methods

#### `screenshot(area=None, path=None) -> np.ndarray`

Captures the screen or a specific `Area`. Optionally saves it to a file.

```python
img = ui.screenshot()
img = ui.screenshot(path="debug.png")
```

#### `mouse_position -> Point`

Property. Returns the current mouse coordinates as a `Point(x, y)`.

#### `screen_size -> tuple[int, int]`

Property. Returns the screen dimensions as `(width, height)`.

#### `connect()`

For VNC mode: establishes the remote session. Must be called before interacting if the driver requires an explicit connection.

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
from guimauve.models.parameters.parameters import Parameters

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
| `default` | `DefaultParams` | see below | Default parameters applied to every element at runtime. |

### VNC Settings

The `vnc` parameter accepts a `VNC` object or a dict. Either `display` or `port` must be specified.

| Field | Type | Default | Description |
|---|---|---|---|
| `host` | `str` | — | Hostname or IP address of the VNC server. |
| `display` | `int` | `None` | X display number (e.g. `1` maps to port `5901`). |
| `port` | `int` | `None` | Explicit TCP port of the VNC server. |
| `password` | `str` | `None` | VNC password. |

```python
from guimauve.models.parameters.vnc import VNC

params = Parameters(
    execution_mode="vnc",
    vnc=VNC(host="192.168.1.10", display=1, password="secret")
)
```

### Screenshot Settings

Controls automatic screenshots captured around actions. Useful for audit trails or debugging.

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
from guimauve.models.parameters.screenshot import Screenshot, ScreenshotActions

params = Parameters(
    screenshot=Screenshot(
        enable=True,
        folder="logs/screenshots",
        limit=100,
        on=ScreenshotActions(locate=False, move=False)
    )
)
```

---

### Default Parameters

`Parameters.default` holds the default values for all detection and interaction settings. When the controller runs an action, it applies these defaults to the element — any field already set on the element or its variants takes precedence. This means `default` acts as the fallback layer at the bottom of the override chain:

```
DefaultParams  <  Element  <  Variant
```

```python
from guimauve.models.parameters.parameters import DefaultParams

params = Parameters(
    default=DefaultParams(
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
| `find_all` | `False` | If `True`, collects matches from all variants instead of stopping at the first successful one. |

#### Mouse

| Parameter | Default | Description |
|---|---|---|
| `mouse_direction` | `MouseDirection.STRAIGHT` | Path the mouse takes when moving: `STRAIGHT`, `XY_X` (horizontal then vertical), or `XY_Y` (vertical then horizontal). |
| `mouse_speed` | `None` | Movement speed in pixels per second. `None` means instant (no animation). |

#### Match Selection

| Parameter | Default | Description |
|---|---|---|
| `match_index` | `0` | When multiple matches are found, which one to use (0-based). |
| `match_sort` | `MatchSort.XY_POSITION` | How to sort matches before selecting: `XY_POSITION` (top-left to bottom-right) or `CONFIDENCE` (best score first). |

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

#### OCR

| Parameter | Default | Description |
|---|---|---|
| `use_ocr` | `False` | Enables EasyOCR-based text detection, used for text variants. |
| `ocr_confidence_threshold` | `0.8` | Minimum OCR engine confidence score (0–1) for a detected region to be considered. |
| `text_threshold` | `0.75` | Minimum score (0–1) for a text match to be accepted. |
| `text_language` | `"en"` | OCR language code. |
| `text_case_sensitive` | `False` | Whether text matching is case-sensitive. |

---

## Elements

An `Element` defines what the controller looks for on screen and how it interacts with it. Elements are typically declared in a YAML file, compiled with `guimauve build`, and accessed as uppercase constants in Python.

Any parameter from `DefaultParams` can be overridden at the element level, and variants can further override a subset of those parameters. The full override chain is:

```
DefaultParams  <  Element  <  Variant
```

### Coordinates

An element can have a fixed screen position instead of (or in addition to) image variants. When coordinates are set, detection is skipped entirely.

| Field | Type | Description |
|---|---|---|
| `x` | `int` | Absolute X coordinate on screen. |
| `y` | `int` | Absolute Y coordinate on screen. |
| `rel_x` | `int` | X offset relative to the current mouse position. |
| `rel_y` | `int` | Y offset relative to the current mouse position. |

`x` and `rel_x` are mutually exclusive, as are `y` and `rel_y`. An element must have at least one set of coordinates or one variant.

### Target

The `target` field defines the exact point to interact with once the element is detected.

- `[x, y]` — pixel offset within the matched bounding box.
- `"TARGET_NAME"` — refers to a named target defined inside a variant.
- If omitted, the center of the matched bounding box is used.

### Variants

Each element can have one or more variants, searched in order. The first variant with a match is used (unless `find_all=True`). Variant names should be uppercase (e.g. `DEFAULT`, `DARK_THEME`, `FRENCH`).

#### Image variants

Match a reference screenshot against the current screen using template or feature matching.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Uppercase identifier for the variant (e.g. `DEFAULT`). |
| `path` | `str` | Path to the reference image file. |
| `targets` | `list` | Named click targets, each defined as `{name, x, y}` offsets within the image. |
| `default_target` | `str` | Name of the target used when no `target` is specified at the element level. |
| `match_area` | `Area` | Crops the reference image before matching, to exclude irrelevant parts of the captured template. |

Detection parameters (`use_template`, `template_confidence_threshold`, `use_feature`, `search_area`, etc.) can all be set per-variant to override element and global defaults.

#### Text variants

Match a string on screen using OCR. Text parameters (`text_threshold`, `text_language`, `text_case_sensitive`) can be set per-variant.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Uppercase identifier for the variant (e.g. `ENGLISH`). |
| `text` | `str` | The text string to search for on screen. |

### Dynamic Elements

Elements can also be instantiated directly in code without a YAML file. This is particularly useful for pure coordinate-based interactions or when building elements programmatically at runtime.

```python
from guimauve.models.element import Element

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
ui.click(on=Elements.BUTTON(mouse_speed=500, search_area=ScreenArea.TOP_HALF))

# Force a specific timeout for this wait only
ui.wait(on=Elements.SLOW_DIALOG(timeout=15))
```

---

## Data Structure (YAML)

Below is a full example of a `.data.yml` file covering all available fields.

```yaml
module: my_app
image_dir: ./images

elements:
  - name: LOGIN_BUTTON
    timeout: 10
    search_area: TOP_HALF         # ScreenArea enum value
    target: PRIMARY               # Named target defined in the variant
    variants:
      - name: DEFAULT
        path: login_button.png
        use_template: true
        template_confidence_threshold: 0.90
        targets:
          - name: PRIMARY
            x: 45
            y: 12

  - name: USERNAME_FIELD
    x: 640
    y: 360                        # Fixed coordinates, no image matching needed

  - name: ERROR_MESSAGE
    use_ocr: true
    variants:
      - name: ENGLISH
        text: "Invalid credentials"
        text_language: en
      - name: FRENCH
        text: "Identifiants invalides"
        text_language: fr

  - name: NOTIFICATION_ICON
    find_all: true
    match_sort: XY_POSITION
    variants:
      - name: ACTIVE
        path: notif_active.png
      - name: INACTIVE
        path: notif_inactive.png
```

---

## Debug Mode

Setting `debug_elements=True` in `Parameters` activates the Integrated Editor automatically whenever:

- An element fails schema validation.
- An element cannot be found on screen within its timeout.

In each case, the editor opens with a contextual message, lets you capture or adjust the element, and then resumes script execution. If the editor is closed without saving, the action returns `None`.

This makes it possible to define and fix elements interactively, without stopping the automation script.