# iOS Shortcuts Action Dictionary — v2.0

Reference for the `generate_shortcut.py` builder API and JSON definition format.

## Quick Start

### Python API
```python
from generate_shortcut import (
    ShortcutBuilder, ref_output, ref_variable, ref_extension_input,
    serialize_dict_field_value, serialize_interpolated_text,
)

builder = ShortcutBuilder(icon_color="blue", icon_glyph="microphone")
builder.set_input_types("app", "av_asset")
builder.set_types("ActionExtension", "WFWorkflowTypeShowInSearch")

h_text = builder.add_action("text", text="hello@example.com")
builder.add_action("set_variable", name="Email", input=ref_output(h_text))
builder.save("my-shortcut.shortcut")
```

### JSON Definition (CLI)
```bash
python3 generate_shortcut.py definition.json output.shortcut
```

---

## Reference Helpers

### `ref_output(handle)` — ActionOutput reference
References a previous action's output via its UUID. The `handle` is the `ActionHandle` returned by `add_action()`.

```python
h = builder.add_action("text", text="hello")
builder.add_action("set_variable", name="Greeting", input=ref_output(h))
```

Produces:
```json
{"Value": {"OutputUUID": "<uuid>", "Type": "ActionOutput", "OutputName": "Text"},
 "WFSerializationType": "WFTextTokenAttachment"}
```

### `ref_variable(name)` — Named variable reference
References a variable previously stored via `set_variable`.

```python
builder.add_action("if", condition="has_any_value", input=ref_variable("WiFiName"))
```

Produces:
```json
{"Value": {"VariableName": "WiFiName", "Type": "Variable"},
 "WFSerializationType": "WFTextTokenAttachment"}
```

### `ref_extension_input()` — Share-sheet input reference
References the input from the share sheet / extension.

```python
builder.add_action("set_variable", name="AudioFile", input=ref_extension_input())
```

Produces:
```json
{"Value": {"Type": "ExtensionInput"},
 "WFSerializationType": "WFTextTokenAttachment"}
```

---

## Interpolated Text

Strings that embed variables use `serialize_interpolated_text(segments)`:

```python
from generate_shortcut import serialize_interpolated_text, ref_variable

value = serialize_interpolated_text(["Hello, ", ref_variable("Name"), "!"])
# Produces WFTextTokenString with U+FFFC markers and attachmentsByRange
```

Segments are a list of `str` (literal text) and `dict` (ref_variable/ref_output results).

Offsets in `attachmentsByRange` use UTF-16 code units (matching Apple's NSString).

---

## Dictionary Field Values

For parameters like `WFHTTPHeaders`, `WFFormValues`, `WFJSONValues`, and `WFItems` (dictionary action), use `serialize_dict_field_value()` or pass a list of dicts to the builder:

```python
builder.add_action("get_url",
    url="https://api.example.com",
    method="POST",
    body_type="Form",
    headers=[
        {"key": "Authorization", "value": "Bearer token123", "type": "text"},
    ],
    form_values=[
        {"key": "file", "value": ref_variable("MyFile"), "type": "file"},
        {"key": "email", "value": ref_variable("Email"), "type": "text"},
        {"key": "greeting", "value": "Hello!", "type": "text"},
    ],
)
```

### Item Types (`WFItemType`)
| Type | Value | Usage |
|---|---|---|
| Text | 0 | String values (plain or interpolated) |
| Dictionary | 1 | Nested dict |
| Array | 2 | Nested array |
| Number | 3 | Numeric value |
| Boolean | 4 | True/False |
| File/Attachment | 5 | Variable reference (files, photos) |

For `type: "file"` entries, the value should be a `ref_variable()` or `ref_output()` — it's wrapped in `WFTokenAttachmentParameterState`.

For `type: "text"` entries, a ref dict is automatically converted to a single-variable interpolated text (U+FFFC with attachmentsByRange).

---

## Condition Map (Conditional Tests)

Used in `add_action("if", condition=..., input=...)`:

| Friendly Name | Integer | Meaning |
|---|---|---|
| `is_less_than` / `less_than` / `lt` | 0 | Numeric less than |
| `is_greater_than` / `greater_than` / `gt` | 2 | Numeric greater than |
| `equals` / `equal` / `eq` | 4 | Exact equality |
| `does_not_equal` / `not_equal` / `neq` / `ne` | 5 | Not equal |
| `contains` | 99 | Substring contains |
| `does_not_contain` / `not_contains` | 999 | Substring does not contain |
| `has_any_value` / `has_value` / `any_value` | 100 | Has any value (non-empty) |

You can pass either the string name or the integer directly.

---

## Control Flow Blocks

### If / Otherwise / End If
```python
builder.add_action("if", condition="has_any_value", input=ref_variable("X"))
# ... actions in the "then" branch ...
builder.add_action("otherwise")
# ... actions in the "else" branch ...
builder.add_action("end_if")
```

GroupingIdentifier is managed automatically. The `otherwise` block is optional.

### Menu / Menu Case / End Menu
```python
builder.add_action("menu", prompt="Choose an option", items=["Option A", "Option B", "Skip"])
builder.add_action("menu_case", title="Option A")
# ... actions for Option A ...
builder.add_action("menu_case", title="Option B")
# ... actions for Option B ...
builder.add_action("menu_case", title="Skip")
# ... actions for Skip (can be empty) ...
builder.add_action("end_menu")
```

Each item in `items` must have a corresponding `menu_case` with matching title.

### Repeat / End Repeat
```python
builder.add_action("repeat", count=5)
# ... loop body ...
builder.add_action("end_repeat")
```

### Repeat Each / End Repeat Each
```python
builder.add_action("repeat_each", input=ref_variable("MyList"))
# ... loop body ...
builder.add_action("end_repeat_each")
```

---

## Icon Color Table

Corrected values (packed RGBA-8 integers):

| Name | Decimal | Hex |
|---|---|---|
| `red` | 4282601983 | FF4351FF |
| `dark_orange` | 4251333119 | FD6631FF |
| `orange` | 4271458815 | FE9949FF |
| `yellow` | 4292093695 | FFD426FF |
| `green` / `teal` | 431817727 | 19BD03FF |
| `light_blue` | 1440408063 | 55DAE1FF |
| `blue` | 463140863 | 1B9AF7FF |
| `dark_blue` | 946986751 | 3871DEFF |
| `purple` | 3679049983 | DB49D8FF |
| `pink` | 3980825855 | ED4694FF |
| `dark_pink` | 3989222655 | EDC3BFFF |
| `gray` | 255 | 000000FF |

Pass the string name or raw integer.

---

## Icon Glyph Table

Common presets:

| Name | Value |
|---|---|
| `shortcut` | 61440 |
| `globe` | 59662 |
| `gear` | 59548 |
| `bell` | 59530 |
| `camera` | 59474 |
| `clipboard` | 61444 |
| `document` | 59493 |
| `folder` | 59508 |
| `heart` | 59458 |
| `home` | 59496 |
| `link` | 59654 |
| `location` | 59519 |
| `lock` | 59636 |
| `mail` | 59500 |
| `music` | 59504 |
| `photo` | 59478 |
| `play` | 59481 |
| `search` | 59574 |
| `share` | 59505 |
| `star` | 59577 |
| `timer` | 59588 |
| `wifi` | 59498 |
| `bolt` | 59459 |
| `cloud` | 59472 |
| `microphone` | 61592 |

For unlisted glyphs, pass the raw integer.

---

## Content Item Classes

Used with `builder.set_input_types()` and `builder.set_output_types()`:

| Shorthand | Full Class Name |
|---|---|
| `text` | WFStringContentItem |
| `url` | WFURLContentItem |
| `image` | WFImageContentItem |
| `pdf` | WFPDFContentItem |
| `file` | WFGenericFileContentItem |
| `web_page` | WFWebPageContentItem |
| `rich_text` | WFRichTextContentItem |
| `phone` | WFPhoneNumberContentItem |
| `email` | WFEmailAddressContentItem |
| `date` | WFDateContentItem |
| `location` | WFLocationContentItem |
| `contact` | WFContactContentItem |
| `app_store_app` | WFAppStoreAppContentItem |
| `map_link` | WFMKMapItemContentItem |
| `safari_web_page` | WFSafariWebPageContentItem |
| `app` | WFAppContentItem |
| `av_asset` | WFAVAssetContentItem |
| `article` | WFArticleContentItem |
| `itunes` | WFiTunesProductContentItem |

You can also pass the full class name directly.

---

## Action Registry

### Text & Variables
| Builder Name | Action Identifier | Key Params |
|---|---|---|
| `text` | `is.workflow.actions.gettext` | `text` |
| `set_variable` | `is.workflow.actions.setvariable` | `name`, `input` (ref) |
| `get_variable` | `is.workflow.actions.getvariable` | `name` |

### User Interaction
| Builder Name | Action Identifier | Key Params |
|---|---|---|
| `ask_input` | `is.workflow.actions.ask` | `prompt`, `input_type`, `default` |
| `alert` | `is.workflow.actions.alert` | `message`, `title`, `show_cancel` |
| `show_result` | `is.workflow.actions.showresult` | `text` |
| `notification` | `is.workflow.actions.notification` | `body`, `title`, `sound` |
| `choose_from_list` | `is.workflow.actions.choosefromlist` | `prompt` |

### Menu (Control Flow Block)
| Builder Name | Action Identifier | Key Params |
|---|---|---|
| `menu` | `is.workflow.actions.choosefrommenu` | `prompt`, `items` (list of strings) |
| `menu_case` | `is.workflow.actions.choosefrommenu` | `title` |
| `end_menu` | `is.workflow.actions.choosefrommenu` | — |

### Web / API
| Builder Name | Action Identifier | Key Params |
|---|---|---|
| `url` | `is.workflow.actions.url` | `url` |
| `open_url` | `is.workflow.actions.openurl` | — |
| `get_url` | `is.workflow.actions.downloadurl` | `url`, `method`, `body_type`, `headers`, `form_values`, `json_values`, `body`, `show_headers` |

### Control Flow
| Builder Name | Action Identifier | Key Params |
|---|---|---|
| `if` | `is.workflow.actions.conditional` | `condition`, `input` (ref), `value` |
| `otherwise` | `is.workflow.actions.conditional` | — |
| `end_if` | `is.workflow.actions.conditional` | — |
| `repeat` | `is.workflow.actions.repeat.count` | `count` |
| `end_repeat` | `is.workflow.actions.repeat.count` | — |
| `repeat_each` | `is.workflow.actions.repeat.each` | `input` (ref) |
| `end_repeat_each` | `is.workflow.actions.repeat.each` | — |
| `wait` | `is.workflow.actions.delay` | `seconds` |
| `comment` | `is.workflow.actions.comment` | `text` |
| `stop` | `is.workflow.actions.exit` | — |
| `nothing` | `is.workflow.actions.nothing` | — |

### Network
| Builder Name | Action Identifier | Key Params |
|---|---|---|
| `get_wifi` | `is.workflow.actions.getwifi` | — |

### Photos
| Builder Name | Action Identifier | Key Params |
|---|---|---|
| `take_photo` | `is.workflow.actions.takephoto` | `show_preview`, `photo_count` |
| `select_photos` | `is.workflow.actions.selectphoto` | `multiple`, `picker_types` |
| `save_to_photo_album` | `is.workflow.actions.savetocameraroll` | — |

### Data
| Builder Name | Action Identifier | Key Params |
|---|---|---|
| `dictionary` | `is.workflow.actions.dictionary` | `items` (list of field dicts) |
| `get_dictionary` | `is.workflow.actions.detect.dictionary` | — |
| `get_dictionary_value` | `is.workflow.actions.getvalueforkey` | `key` |
| `set_dictionary_value` | `is.workflow.actions.setvalueforkey` | `key`, `value` |
| `count` | `is.workflow.actions.count` | `type` |
| `list` | `is.workflow.actions.list` | `items` |

### Date/Time
| Builder Name | Action Identifier | Key Params |
|---|---|---|
| `date` | `is.workflow.actions.date` | `mode` |
| `format_date` | `is.workflow.actions.format.date` | `style`, `format` |

### Device
| Builder Name | Action Identifier | Key Params |
|---|---|---|
| `get_battery_level` | `is.workflow.actions.getbatterylevel` | — |
| `get_device_details` | `is.workflow.actions.getdevicedetails` | `detail` |
| `set_brightness` | `is.workflow.actions.setbrightness` | `level` |
| `set_volume` | `is.workflow.actions.setvolume` | `level` |

### Sharing / Files
| Builder Name | Action Identifier | Key Params |
|---|---|---|
| `share` | `is.workflow.actions.share` | — |
| `airdrop` | `is.workflow.actions.airdropdocument` | — |
| `get_file` | `is.workflow.actions.documentpicker.open` | `multiple` |
| `save_file` | `is.workflow.actions.documentpicker.save` | `path`, `ask_where` |

### Debug
| Builder Name | Action Identifier | Key Params |
|---|---|---|
| `quick_look` | `is.workflow.actions.previewdocument` | — |
| `view_content_graph` | `is.workflow.actions.viewresult` | — |

### Escape Hatch
| Builder Name | Key Params |
|---|---|
| `raw` | `identifier`, `parameters` (dict) |

---

## JSON Definition Schema

### Top-Level
```json
{
  "icon": {"color": "blue", "glyph": "microphone"},
  "input_types": ["app", "av_asset"],
  "output_types": [],
  "types": ["ActionExtension", "WFWorkflowTypeShowInSearch"],
  "import_questions": [],
  "actions": [...]
}
```

### Action Objects
```json
{"type": "text", "text": "hello@example.com", "label": "email_text"}
```

The `label` field (optional) names the action's output for later reference.

### Reference Syntax in JSON
```json
{"var": "VariableName"}         // ref_variable()
{"output": "label_name"}       // ref_output() by label
{"input": true}                // ref_extension_input()
```

Used in `input` fields and dict field `value` entries.

### Dict Field Items
```json
{"key": "auth", "value": "token123", "type": "text"}
{"key": "file", "value": {"var": "MyFile"}, "type": "file"}
{"key": "email", "value": [{"var": "Email"}], "type": "text"}
```

For `type: "text"` with a variable, wrap in an array (interpolated text segments). A lone `{"var": ...}` is auto-promoted to `[{"var": ...}]`.

---

## Complete Worked Example: Voice Memo Upload

```json
{
  "icon": {"color": "blue", "glyph": 61592},
  "input_types": ["WFAppContentItem", "WFAVAssetContentItem"],
  "types": ["ActionExtension", "WFWorkflowTypeShowInSearch"],
  "import_questions": [
    {"prompt": "Upload token:", "variable": "uploadToken"}
  ],
  "actions": [
    {"type": "set_variable", "name": "AudioFile", "input": {"input": true}},
    {"type": "text", "text": "someone@example.com", "label": "email_text"},
    {"type": "set_variable", "name": "Email", "input": {"output": "email_text"}},
    {"type": "get_wifi", "label": "wifi"},
    {"type": "set_variable", "name": "WiFiName", "input": {"output": "wifi"}},
    {"type": "if", "condition": "has_any_value", "input": {"var": "WiFiName"}},
    {"type": "otherwise"},
    {"type": "menu", "prompt": "No Wi-Fi. Continue?", "items": ["Upload", "Cancel"]},
    {"type": "menu_case", "title": "Upload"},
    {"type": "menu_case", "title": "Cancel"},
    {"type": "stop"},
    {"type": "end_menu"},
    {"type": "end_if"},
    {"type": "ask_input", "prompt": "Any notes?", "label": "notes"},
    {"type": "set_variable", "name": "Notes", "input": {"output": "notes"}},
    {"type": "get_url",
     "url": "https://api.example.com/upload",
     "method": "POST",
     "body_type": "Form",
     "headers": [{"key": "Authorization", "value": ["Bearer ", {"var": "uploadToken"}], "type": "text"}],
     "form_values": [
       {"key": "audio", "value": {"var": "AudioFile"}, "type": "file"},
       {"key": "email", "value": [{"var": "Email"}], "type": "text"},
       {"key": "notes", "value": [{"var": "Notes"}], "type": "text"}
     ]
    },
    {"type": "notification", "body": "Upload complete!", "title": "Voice Memo Upload"}
  ]
}
```

---

## Top-Level Metadata (for reference)

The builder produces these top-level plist keys:

| Key | Default | Notes |
|---|---|---|
| `WFWorkflowMinimumClientVersion` | 900 | iOS 14+ compat floor |
| `WFWorkflowMinimumClientVersionString` | "900" | Stringified version |
| `WFWorkflowClientVersion` | "4528.0.4.2" | Build string |
| `WFWorkflowIcon` | color + glyph | Icon dict |
| `WFWorkflowActions` | [] | Action list |
| `WFWorkflowHasOutputFallback` | false | |
| `WFWorkflowOutputContentItemClasses` | [] | |
| `WFWorkflowInputContentItemClasses` | [] | Set via `set_input_types()` |
| `WFWorkflowImportQuestions` | [] | Set via `add_import_question()` |
| `WFQuickActionSurfaces` | [] | |
| `WFWorkflowTypes` | [] | Set via `set_types()` |
| `WFWorkflowHasShortcutInputVariables` | false | Auto-set when input types present |

**Note:** No `WFWorkflowName` key is emitted. The shortcut name comes from the filename.