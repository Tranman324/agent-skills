"""Offline tests for the iOS Shortcuts generator.

Everything here is synthetic: no real endpoints, accounts, or tokens.
The worked example in references/action-dictionary.md is built as a regression case,
so the docs and the generator can't drift apart silently.
"""
import json
import plistlib
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(SKILL / "scripts"))

from generate_shortcut import (  # noqa: E402
    CONDITION_MAP,
    ShortcutBuilder,
    build_from_definition,
    ref_extension_input,
    ref_output,
    ref_variable,
)


def actions_by_id(plist, ident):
    return [a for a in plist["WFWorkflowActions"] if a["WFWorkflowActionIdentifier"] == ident]


def build_voice_memo_upload() -> ShortcutBuilder:
    """A synthetic share-sheet upload shortcut using the main control-flow features."""
    b = ShortcutBuilder(icon_color="blue", icon_glyph=61592)
    b.set_input_types("app", "av_asset")
    b.set_types("ActionExtension", "WFWorkflowTypeShowInSearch")
    b.add_import_question("Upload token:", "uploadToken")

    b.add_action("comment", text="Purpose: upload a voice memo. Trigger: Share Sheet.")
    b.add_action("set_variable", name="AudioFile", input=ref_extension_input())
    b.add_action("if", condition="has_any_value", input=ref_variable("AudioFile"))
    b.add_action("otherwise")
    b.add_action("alert", title="No audio", message="Share a voice memo to this shortcut.")
    b.add_action("stop")
    b.add_action("end_if")
    b.add_action("menu", prompt="Upload now?", items=["Upload", "Cancel"])
    b.add_action("menu_case", title="Upload")
    b.add_action("menu_case", title="Cancel")
    b.add_action("stop")
    b.add_action("end_menu")
    notes = b.add_action("ask_input", prompt="Any notes?")
    b.add_action("set_variable", name="Notes", input=ref_output(notes))
    b.add_action(
        "get_url",
        url="https://api.example.com/upload",
        method="POST",
        body_type="Form",
        headers=[{"key": "Authorization", "value": ["Bearer ", ref_variable("uploadToken")], "type": "text"}],
        form_values=[
            {"key": "audio", "value": ref_variable("AudioFile"), "type": "file"},
            {"key": "notes", "value": [ref_variable("Notes")], "type": "text"},
        ],
    )
    b.add_action("notification", title="Voice Memo Upload", body="Upload complete!")
    return b


class BuilderOutput(unittest.TestCase):
    def setUp(self):
        self.b = build_voice_memo_upload()
        self.plist = self.b.build()

    def test_validates_clean(self):
        self.assertEqual(self.b.validate(), [])

    def test_top_level_metadata(self):
        p = self.plist
        self.assertEqual(p["WFWorkflowIcon"]["WFWorkflowIconGlyphNumber"], 61592)
        self.assertEqual(p["WFWorkflowTypes"], ["ActionExtension", "WFWorkflowTypeShowInSearch"])
        self.assertTrue(p["WFWorkflowHasShortcutInputVariables"])
        self.assertEqual(len(p["WFWorkflowInputContentItemClasses"]), 2)
        q = p["WFWorkflowImportQuestions"][0]
        self.assertEqual(q["WFWorkflowImportQuestionVariable"], "uploadToken")

    def test_control_flow_grouping(self):
        ifs = actions_by_id(self.plist, "is.workflow.actions.conditional")
        modes = [a["WFWorkflowActionParameters"]["WFControlFlowMode"] for a in ifs]
        self.assertEqual(modes, [0, 1, 2])
        groups = {a["WFWorkflowActionParameters"]["GroupingIdentifier"] for a in ifs}
        self.assertEqual(len(groups), 1, "if/otherwise/end_if must share one GroupingIdentifier")
        self.assertEqual(ifs[0]["WFWorkflowActionParameters"]["WFCondition"], CONDITION_MAP["has_any_value"])
        self.assertIn("WFInput", ifs[0]["WFWorkflowActionParameters"])

        menus = actions_by_id(self.plist, "is.workflow.actions.choosefrommenu")
        self.assertEqual([a["WFWorkflowActionParameters"]["WFControlFlowMode"] for a in menus], [0, 1, 1, 2])
        self.assertEqual(len({a["WFWorkflowActionParameters"]["GroupingIdentifier"] for a in menus}), 1)
        self.assertNotEqual(groups, {menus[0]["WFWorkflowActionParameters"]["GroupingIdentifier"]})

    def test_magic_variable_chaining(self):
        ask = actions_by_id(self.plist, "is.workflow.actions.ask")[0]
        out_uuid = ask["WFWorkflowActionParameters"]["UUID"]
        dumped = json.dumps(self.plist, default=str)
        self.assertGreaterEqual(dumped.count(out_uuid), 2, "ask output UUID must be referenced downstream")

    def test_http_form_and_headers(self):
        req = actions_by_id(self.plist, "is.workflow.actions.downloadurl")[0]["WFWorkflowActionParameters"]
        self.assertEqual(req["WFHTTPMethod"], "POST")
        self.assertEqual(req["WFHTTPBodyType"], "Form")
        self.assertTrue(req["ShowHeaders"])
        self.assertEqual(req["WFHTTPHeaders"]["WFSerializationType"], "WFDictionaryFieldValue")
        form = req["WFFormValues"]["Value"]["WFDictionaryFieldValueItems"]
        audio = form[0]
        self.assertEqual(audio["WFItemType"], 5)  # file attachment
        self.assertEqual(audio["WFValue"]["WFSerializationType"], "WFTokenAttachmentParameterState")
        self.assertEqual(form[1]["WFValue"]["WFSerializationType"], "WFTextTokenString")

    def test_binary_plist_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.b.save(str(Path(d) / "x.shortcut"))
            raw = path.read_bytes()
            self.assertTrue(raw.startswith(b"bplist00"))
            loaded = plistlib.loads(raw)
            buf1 = plistlib.dumps(loaded, fmt=plistlib.FMT_BINARY)
            buf2 = plistlib.dumps(plistlib.loads(buf1), fmt=plistlib.FMT_BINARY)
            self.assertEqual(buf1, buf2)
            self.assertEqual(len(loaded["WFWorkflowActions"]), len(self.plist["WFWorkflowActions"]))


class Validator(unittest.TestCase):
    def test_unclosed_if(self):
        b = ShortcutBuilder()
        b.add_action("if", condition="equals", input=ref_variable("x"), value="y")
        self.assertTrue(any("Unclosed" in w for w in b.validate()))

    def test_unclosed_menu(self):
        b = ShortcutBuilder()
        b.add_action("menu", prompt="Pick", items=["A", "B"])
        b.add_action("menu_case", title="A")
        self.assertTrue(any("Unclosed" in w for w in b.validate()))

    def test_conditional_without_input(self):
        b = ShortcutBuilder()
        b.add_action("if", condition="equals")
        b.add_action("end_if")
        self.assertTrue(any("WFInput" in w for w in b.validate()))

    def test_menu_case_outside_menu(self):
        b = ShortcutBuilder()
        b.actions.append({
            "WFWorkflowActionIdentifier": "is.workflow.actions.choosefrommenu",
            "WFWorkflowActionParameters": {"WFControlFlowMode": 1, "WFMenuItemTitle": "orphan"},
        })
        self.assertTrue(any("menu_case outside" in w for w in b.validate()))

    def test_empty_shortcut(self):
        self.assertTrue(any("no actions" in w for w in ShortcutBuilder().validate()))

    def test_unknown_action_rejected(self):
        with self.assertRaises(ValueError):
            ShortcutBuilder().add_action("definitely_not_real")


class DocsExamples(unittest.TestCase):
    def _worked_example(self) -> dict:
        md = (SKILL / "references" / "action-dictionary.md").read_text()
        section = md.split("## Complete Worked Example", 1)[1]
        block = re.search(r"```json\n(.*?)\n```", section, re.S).group(1)
        return json.loads(block)

    def test_worked_example_builds_clean(self):
        definition = self._worked_example()
        with tempfile.TemporaryDirectory() as d:
            path = build_from_definition(definition, str(Path(d) / "example.shortcut"))
            plist = plistlib.loads(path.read_bytes())
        idents = [a["WFWorkflowActionIdentifier"] for a in plist["WFWorkflowActions"]]
        self.assertIn("is.workflow.actions.downloadurl", idents)
        self.assertEqual(idents[-1], "is.workflow.actions.notification")

    def test_cli_entry_point(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "def.json").write_text(json.dumps(self._worked_example()))
            r = subprocess.run(
                [sys.executable, str(SKILL / "scripts" / "generate_shortcut.py"), str(d / "def.json"), str(d / "o.shortcut")],
                capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stderr.strip(), "", "worked example should build without validator warnings")
            self.assertTrue((d / "o.shortcut").read_bytes().startswith(b"bplist00"))

    def test_skill_md_python_example_runs(self):
        md = (SKILL / "SKILL.md").read_text()
        code = re.search(r"\*\*1\. Python API.*?```python\n(.*?)\n```", md, re.S).group(1)
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run(
                [sys.executable, "-c", code], cwd=d, capture_output=True, text=True,
                env={"PYTHONPATH": str(SKILL / "scripts")},
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((Path(d) / "my-shortcut.shortcut").exists())


if __name__ == "__main__":
    unittest.main()
