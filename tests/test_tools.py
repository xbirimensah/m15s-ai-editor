#!/usr/bin/env python3
"""Unit tests for the m15s-ai-editor tools that need no footage.

    python3 tests/test_tools.py        (venv Python: PyYAML is needed)
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


class TempHome(unittest.TestCase):
    """Every test gets its own config home and workspace."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.ws = Path(self.tmp.name) / "ws"
        self.home.mkdir()
        os.environ["M15S_EDITOR_HOME"] = str(self.home)
        os.environ["M15S_WORKSPACE"] = str(self.ws)

    def tearDown(self):
        os.environ.pop("M15S_EDITOR_HOME", None)
        os.environ.pop("M15S_WORKSPACE", None)
        self.tmp.cleanup()

    def creator(self, text):
        (self.home / "creator.yaml").write_text(text)


class ConfigTest(TempHome):
    def test_paths_follow_env_and_creator(self):
        import config
        self.assertEqual(config.home(), self.home)
        self.assertEqual(config.workspace(), self.ws)
        self.creator("delivery_dir: ~/out-folder\npronunciation_fixes:\n  Cloud: Claude\n")
        self.assertEqual(config.delivery_dir(), Path("~/out-folder").expanduser())
        self.assertEqual(config.pronunciation_fixes(), {"Cloud": "Claude"})
        self.assertEqual(config.work_dir("a-b"), self.ws / "work" / "a-b")


class PrivacyTest(TempHome):
    def scan(self, files):
        import privacy_check
        repo = Path(self.tmp.name) / "repo"
        for name, text in files.items():
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text(text)
        return privacy_check.scan(repo)

    def test_private_terms_and_creator_values_are_blocked(self):
        (self.home / "private-terms.txt").write_text("# comment\nSecretClient\n")
        self.creator("creator:\n  name: Jane Example\n  instagram: '@jane.example'\nbrand:\n  colors:\n    accent: '#A1B2C3'\n")
        hits = self.scan({"a.md": "made for secretclient\n", "b.ts": "color: '#a1b2c3'\n",
                          "c.md": "by Jane Example\n", "d.md": "nothing here\n"})
        self.assertEqual(len(hits), 3, hits)

    def test_generic_patterns(self):
        hits = self.scan({"a.py": "p = '/Users/someone/x'\nq = '/Users/me/x'\n",  # privacy: allow
                          "b.md": "mail jane@realmail.de or noreply@example.com\n",  # privacy: allow
                          "c.sh": "KEY=gsk_" + "a" * 30 + "\n",
                          "d.md": "/Volumes/<disk>/ and /Volumes/Data/x privacy: allow\n"})
        kinds = sorted(h.split(": ")[1].split(" ")[0] for h in hits)
        self.assertEqual(kinds, ["api", "email", "home"], hits)


class TasteTest(TempHome):
    def taste(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "tools" / "taste.py"), *args],
                              capture_output=True, text=True, env=os.environ)

    def test_add_show_report(self):
        self.assertEqual(self.taste("add", "captions", "captions one line, below the head").returncode, 0)
        self.assertIn("one line", self.taste("show", "--video", "x").stdout)
        self.assertTrue((self.home / "taste.json").exists())
        self.assertTrue((self.home / "TASTE.md").exists())
        self.assertEqual(self.taste("report").returncode, 0)


class DeliverTest(unittest.TestCase):
    def test_label_slug(self):
        import deliver
        self.assertEqual(deliver.label_slug("Cut v1"), "cut-v1")
        self.assertEqual(deliver.label_slug("final APPROVED"), "final-APPROVED")


class MotionTest(TempHome):
    def spec(self, beats, total=300):
        return {"durationInFrames": total, "fps": 30, "captions": {"enabled": True, "y": 1200}, "beats": beats}

    def findings(self, spec):
        import motion
        d = self.ws / "work" / "t"
        d.mkdir(parents=True, exist_ok=True)
        (d / "meta.json").write_text(json.dumps({"aspect": "916"}))
        motion.seconds = lambda _p: spec["durationInFrames"] / 30   # no real cut needed
        return motion.plan_findings(spec, d)

    def test_hookbar_must_be_three_seconds(self):
        fails, _ = self.findings(self.spec([{"type": "hookbar", "from": 0, "dur": 30, "text": "x"}]))
        self.assertTrue(any("hook bar" in f for f in fails), fails)
        fails, _ = self.findings(self.spec([{"type": "hookbar", "from": 0, "dur": 90, "text": "x"}]))
        self.assertFalse(fails, fails)

    def test_cues_dates_and_dashes(self):
        beats = [{"type": "hookbar", "from": 0, "dur": 90, "text": "Hook"},
                 {"type": "panel", "from": 100, "dur": 60, "title": "Since March",
                  "rows": [{"text": "one — two", "at": 200}]},
                 {"type": "stat", "from": 200, "dur": 60, "value": "2000", "label": "clients"}]
        fails, _ = self.findings(self.spec(beats))
        joined = " | ".join(fails)
        self.assertIn("cue 200 outside", joined)
        self.assertIn("em dash", joined)
        self.assertIn("a date", joined)
        self.assertNotIn("'2000'", joined)

    def test_still_frames_cover_every_beat(self):
        import motion
        spec = self.spec([{"type": "hookbar", "from": 0, "dur": 90, "text": "x"},
                          {"type": "list", "from": 100, "dur": 120, "items": ["a", "b"], "itemAt": [110, 150]}], 600)
        frames = motion.still_frames(spec)
        labels = [l for _, l in frames]
        self.assertEqual(labels[:2], ["01-hookbar", "02-list"])
        self.assertTrue(any(l.startswith("zz-captions") for l in labels))
        self.assertEqual(dict((l, f) for f, l in frames)["02-list"], 168)


class CutflowTest(TempHome):
    def test_format_pick(self):
        import cutflow
        self.assertEqual(cutflow.pick_format(2160, 3840, "916"), ("916_4k", "cover"))
        self.assertEqual(cutflow.pick_format(1080, 1920, "916"), ("916", "cover"))
        self.assertEqual(cutflow.pick_format(3840, 2160, "916"), ("916", "cover"))
        self.assertEqual(cutflow.pick_format(3840, 2160, "169"), ("169_4k", "cover"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
