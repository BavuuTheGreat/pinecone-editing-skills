"""Tests for check_manifests.py.  Run:  python3 -m unittest discover -s scripts -v"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_manifests as cm  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class Tree(unittest.TestCase):
    def setUp(self):
        self.r = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.r)
        desc = "alpha (does a), beta skills."
        write(f"{self.r}/.claude-plugin/marketplace.json", json.dumps(
            {"name": "m", "plugins": [{"name": "p", "source": "./plugins/p", "version": "1.0.0", "description": desc}]}))
        write(f"{self.r}/plugins/p/.claude-plugin/plugin.json", json.dumps({"name": "p", "version": "1.0.0", "description": desc}))
        write(f"{self.r}/README.md", "uses alpha and beta\n")
        for s in ("alpha", "beta"):
            self.skill(s)

    def skill(self, folder, name=None, desc="d"):
        write(f"{self.r}/plugins/p/skills/{folder}/SKILL.md", f"---\nname: {name or folder}\ndescription: {desc}\n---\nbody\n")

    def test_clean(self):
        self.assertEqual(cm.check(self.r), [])

    def test_version_drift(self):
        write(f"{self.r}/plugins/p/.claude-plugin/plugin.json", json.dumps({"name": "p", "version": "1.0.1", "description": "alpha beta"}))
        self.assertTrue(any("version drift" in e for e in cm.check(self.r)))

    def test_bad_json(self):
        write(f"{self.r}/plugins/p/.claude-plugin/plugin.json", "{nope")
        self.assertTrue(any("cannot parse" in e for e in cm.check(self.r)))

    def test_missing_source(self):
        shutil.rmtree(f"{self.r}/plugins/p")
        self.assertTrue(any("source path" in e for e in cm.check(self.r)))

    def test_name_not_folder(self):
        self.skill("alpha", name="other")
        self.assertTrue(any("!= folder" in e for e in cm.check(self.r)))

    def test_missing_description(self):
        self.skill("alpha", desc="")
        self.assertTrue(any("description missing" in e for e in cm.check(self.r)))

    def test_missing_skill_md(self):
        os.remove(f"{self.r}/plugins/p/skills/beta/SKILL.md")
        self.assertTrue(any("SKILL.md missing" in e for e in cm.check(self.r)))

    def test_skill_not_in_readme(self):
        write(f"{self.r}/README.md", "only alpha\n")
        self.assertTrue(any("beta: not mentioned" in e for e in cm.check(self.r)))

    def test_described_skill_missing(self):
        d = "alpha, beta, ghost-skill"
        write(f"{self.r}/plugins/p/.claude-plugin/plugin.json", json.dumps({"name": "p", "version": "1.0.0", "description": d}))
        self.assertTrue(any("ghost-skill" in e for e in cm.check(self.r)))


class RealRepo(unittest.TestCase):
    def test_repo_is_clean(self):
        self.assertEqual(cm.check(REPO), [])


if __name__ == "__main__":
    unittest.main()
