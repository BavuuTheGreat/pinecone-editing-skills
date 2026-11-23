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
        write(f"{self.r}/docs/SKILLS.md", "alpha and beta\n")
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


    def test_skill_not_in_skills_doc(self):
        write(f"{self.r}/docs/SKILLS.md", "only alpha\n")
        self.assertTrue(any("beta: not mentioned in docs/SKILLS.md" in e for e in cm.check(self.r)))

    def test_skills_doc_missing(self):
        os.remove(f"{self.r}/docs/SKILLS.md")
        self.assertTrue(any("docs/SKILLS.md: missing" in e for e in cm.check(self.r)))

    def test_stale_name_in_manifest(self):
        d = "alpha, beta, brand-motion"
        write(f"{self.r}/plugins/p/.claude-plugin/plugin.json", json.dumps({"name": "p", "version": "1.0.0", "description": d}))
        self.assertTrue(any("old skill name 'brand-motion'" in e for e in cm.check(self.r)))

    def test_stale_name_in_skill_frontmatter(self):
        self.skill("alpha", desc="uses testimonial-reel")
        self.assertTrue(any("old skill name 'testimonial-reel'" in e for e in cm.check(self.r)))

    def test_stale_name_in_ci(self):
        write(f"{self.r}/.github/workflows/ci.yml", "ENGINE: plugins/x/skills/testimonial-reel/engine\n")
        self.assertTrue(any("ci.yml" in e and "testimonial-reel" in e for e in cm.check(self.r)))

    def test_required_skill_missing_for_pinecone_video(self):
        d = "alpha, beta"
        write(f"{self.r}/.claude-plugin/marketplace.json", json.dumps(
            {"name": "m", "plugins": [{"name": "pinecone-video", "source": "./plugins/p", "version": "1.0.0", "description": d}]}))
        write(f"{self.r}/plugins/p/.claude-plugin/plugin.json", json.dumps({"name": "pinecone-video", "version": "1.0.0", "description": d}))
        errs = cm.check(self.r)
        self.assertTrue(any("required skill 'loop-engineer'" in e for e in errs))
        self.assertTrue(any("required skill 'ecc-triage'" in e for e in errs))


class RealRepo(unittest.TestCase):
    def test_repo_is_clean(self):
        self.assertEqual(cm.check(REPO), [])


if __name__ == "__main__":
    unittest.main()
