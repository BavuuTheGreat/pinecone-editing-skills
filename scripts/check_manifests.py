#!/usr/bin/env python3
"""Install-manifest integrity check (stdlib only). Exit 0 = clean, 1 = problems (printed one per line).

Checks:
  - .claude-plugin/marketplace.json and every plugin.json parse
  - marketplace entry version == plugin.json version; plugin `source` path exists
  - every skills/<folder> has SKILL.md whose frontmatter has name + description and name == folder
  - every skill named in the plugin description exists as a folder
  - every skill folder is mentioned in README.md and docs/SKILLS.md
  - the pinecone-video plugin ships the required process skills (loop-engineer, ecc-triage)
  - no manifest, SKILL.md frontmatter or CI file still uses a renamed skill's old name
Run from anywhere:  python3 scripts/check_manifests.py [repo-root]
"""
import json
import os
import re
import sys

REQUIRED = {"pinecone-video": ("loop-engineer", "ecc-triage")}
# old skill name -> new name (renamed in 0.6.0). README.md and docs/SKILLS.md may mention them in "renamed from" notes.
RENAMED = {"testimonial-reel": "interview-reel", "ai-video-playbook": "reel-planner", "brand-motion": "brand-templates"}
SKILL_TOKEN = re.compile(r"(?<![\w-])[a-z][a-z0-9]*(?:-[a-z0-9]+)+(?![\w-])")


def frontmatter(path):
    """Top-level `key: value` pairs of the leading --- block (no YAML dependency)."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    out = {}
    for ln in lines[1:]:
        if ln.strip() == "---":
            return out
        m = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", ln)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return None  # never closed


def load_json(path, errs):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        errs.append(f"{os.path.relpath(path)}: cannot parse ({e})")
        return None


def stale_names(text, where, errs):
    for old, new in RENAMED.items():
        if old in text:
            errs.append(f"{where}: old skill name {old!r} (now {new!r})")


def check(root):
    errs = []
    market = load_json(os.path.join(root, ".claude-plugin", "marketplace.json"), errs)
    if market is None:
        return errs
    plugins = market.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        return errs + ["marketplace.json: no plugins list"]
    readme_path = os.path.join(root, "README.md")
    readme = open(readme_path, encoding="utf-8").read() if os.path.exists(readme_path) else ""
    if not readme:
        errs.append("README.md: missing or empty")
    skills_doc_path = os.path.join(root, "docs", "SKILLS.md")
    skills_doc = open(skills_doc_path, encoding="utf-8").read() if os.path.exists(skills_doc_path) else ""
    if not skills_doc:
        errs.append("docs/SKILLS.md: missing or empty")
    ci_path = os.path.join(root, ".github", "workflows", "ci.yml")
    if os.path.exists(ci_path):
        stale_names(open(ci_path, encoding="utf-8").read(), ".github/workflows/ci.yml", errs)
    for entry in plugins:
        name = entry.get("name", "?")
        stale_names(entry.get("description", ""), f"marketplace.json ({name})", errs)
        src = os.path.join(root, entry.get("source", ""))
        if not entry.get("source") or not os.path.isdir(src):
            errs.append(f"{name}: source path {entry.get('source')!r} does not exist")
            continue
        pj = load_json(os.path.join(src, ".claude-plugin", "plugin.json"), errs)
        if pj is None:
            continue
        if pj.get("name") != name:
            errs.append(f"{name}: plugin.json name is {pj.get('name')!r}")
        if pj.get("version") != entry.get("version"):
            errs.append(f"{name}: version drift, marketplace {entry.get('version')!r} vs plugin.json {pj.get('version')!r}")
        stale_names(pj.get("description", ""), f"{name}/plugin.json", errs)
        skills_dir = os.path.join(src, "skills")
        folders = sorted(d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))) if os.path.isdir(skills_dir) else []
        for d in folders:
            sk = os.path.join(skills_dir, d, "SKILL.md")
            if not os.path.exists(sk):
                errs.append(f"{name}/{d}: SKILL.md missing")
                continue
            fm = frontmatter(sk)
            if fm is None:
                errs.append(f"{name}/{d}: SKILL.md has no frontmatter")
                continue
            if not fm.get("name"):
                errs.append(f"{name}/{d}: frontmatter name missing")
            elif fm["name"] != d:
                errs.append(f"{name}/{d}: frontmatter name {fm['name']!r} != folder")
            if not fm.get("description"):
                errs.append(f"{name}/{d}: frontmatter description missing")
            stale_names(" ".join(fm.values()), f"{name}/{d} SKILL.md frontmatter", errs)
            if d not in readme:
                errs.append(f"{name}/{d}: not mentioned in README.md")
            if skills_doc and d not in skills_doc:
                errs.append(f"{name}/{d}: not mentioned in docs/SKILLS.md")
        for req in REQUIRED.get(name, ()):
            if req not in folders:
                errs.append(f"{name}: required skill {req!r} missing")
        for desc in {entry.get("description", ""), pj.get("description", "")}:
            for tok in sorted(set(SKILL_TOKEN.findall(desc))):
                if tok not in folders:
                    errs.append(f"{name}: description names skill {tok!r} but skills/{tok} does not exist")
    return errs


def main(argv):
    root = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    errs = check(root)
    for e in errs:
        print("FAIL", e)
    print("manifests OK" if not errs else f"{len(errs)} problem(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
