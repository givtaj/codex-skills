#!/usr/bin/env python3
"""Validate portable invariants for the public plugin marketplace."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = ROOT / ".agents" / "plugins" / "marketplace.json"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(
    r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
MODEL_VERSION_RE = re.compile(
    r"(?i)\b(?:gpt|claude|gemini|llama)[- ]?\d+(?:\.\d+)*\b"
)
USER_ROOT = "/" + "Users/"
HOME_ROOT = "/" + "home/"
PERSONAL_PATH_RE = re.compile(
    rf"(?:{re.escape(USER_ROOT)}[^/\s`]+|{re.escape(HOME_ROOT)}[^/\s`]+|(?i:[A-Z]:\\Users\\[^\\\s`]+))"
)
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PRIVATE_KEY_MARKER_RE = re.compile(
    "-----BEGIN " + r"(?:OPENSSH|RSA|DSA|EC|PGP)? ?PRIVATE KEY-----"
)
SENSITIVE_TEXT_PATTERNS = {
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "private key": PRIVATE_KEY_MARKER_RE,
}
INSTALL_POLICIES = {"AVAILABLE", "INSTALLED_BY_DEFAULT", "NOT_AVAILABLE"}
AUTH_POLICIES = {"ON_INSTALL", "ON_USE"}
MARKETPLACE_CATEGORIES = {
    "Business & Operations",
    "Communication",
    "Creativity",
    "Data & Analytics",
    "Developer Tools",
    "Education & Research",
    "Finance",
    "Productivity",
    "Security",
}
REQUIRED_EVAL_KINDS = {
    "direct",
    "indirect",
    "incomplete",
    "follow_up",
    "boundary",
    "negative",
    "edge",
}
EXPECTED_ACTIVATIONS = {
    "activate",
    "activate_if_context_supplies_subject",
    "do_not_activate",
}
REQUIRED_PLUGIN_INTERFACE_STRINGS = {
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
    "websiteURL",
    "privacyPolicyURL",
}
REQUIRED_AGENT_FIELDS = {
    "display_name",
    "short_description",
    "default_prompt",
}


class ValidationError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"missing file: {relative(path)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON in {relative(path)}: {exc}") from exc
    require(isinstance(value, dict), f"expected JSON object: {relative(path)}")
    return value


def frontmatter(skill_md: Path) -> dict[str, str]:
    lines = skill_md.read_text(encoding="utf-8").splitlines()
    require(lines and lines[0].strip() == "---", f"missing frontmatter: {relative(skill_md)}")
    try:
        closing = next(
            i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration as exc:
        raise ValidationError(f"unterminated frontmatter: {relative(skill_md)}") from exc

    values: dict[str, str] = {}
    for line in lines[1:closing]:
        match = re.match(r"^(name|description):\s*(.+?)\s*$", line)
        if match:
            values[match.group(1)] = match.group(2).strip("\"'")
    return values


def validate_agent_metadata(skill_root: Path) -> None:
    metadata_path = skill_root / "agents" / "openai.yaml"
    require(metadata_path.is_file(), f"missing OpenAI metadata: {relative(metadata_path)}")
    text = metadata_path.read_text(encoding="utf-8")
    for field in REQUIRED_AGENT_FIELDS:
        require(
            re.search(rf"^\s*{re.escape(field)}:\s*\S", text, re.MULTILINE) is not None,
            f"{relative(metadata_path)}: missing {field}",
        )
    require(
        re.search(r"^\s*allow_implicit_invocation:\s*(?:true|false)\s*$", text, re.MULTILINE)
        is not None,
        f"{relative(metadata_path)}: missing allow_implicit_invocation policy",
    )


def validate_eval(plugin_dir: Path, skill_name: str) -> None:
    eval_path = plugin_dir / "evals" / f"{skill_name}.json"
    payload = load_json(eval_path)
    require(payload.get("schema_version") == 1, f"{relative(eval_path)}: unsupported schema")
    require(payload.get("skill") == skill_name, f"{relative(eval_path)}: skill mismatch")
    cases = payload.get("cases")
    require(isinstance(cases, list) and cases, f"{relative(eval_path)}: cases must be non-empty")

    ids: set[str] = set()
    kinds: set[str] = set()
    for case in cases:
        require(isinstance(case, dict), f"{relative(eval_path)}: each case must be an object")
        case_id = case.get("id")
        require(
            isinstance(case_id, str) and NAME_RE.fullmatch(case_id),
            f"{relative(eval_path)}: invalid case id {case_id!r}",
        )
        require(case_id not in ids, f"{relative(eval_path)}: duplicate case id {case_id}")
        ids.add(case_id)

        kind = case.get("kind")
        require(kind in REQUIRED_EVAL_KINDS, f"{relative(eval_path)}: invalid kind {kind!r}")
        kinds.add(kind)
        require(
            isinstance(case.get("prompt"), str) and case["prompt"].strip(),
            f"{relative(eval_path)}: {case_id} has no prompt",
        )
        require(
            case.get("expected_activation") in EXPECTED_ACTIVATIONS,
            f"{relative(eval_path)}: {case_id} has invalid expected activation",
        )
        behavior = case.get("expected_behavior")
        require(
            isinstance(behavior, list)
            and behavior
            and all(isinstance(item, str) and item.strip() for item in behavior),
            f"{relative(eval_path)}: {case_id} needs observable expected behavior",
        )

    missing = REQUIRED_EVAL_KINDS - kinds
    require(not missing, f"{relative(eval_path)}: missing case kinds {sorted(missing)}")

    result_files = sorted((plugin_dir / "evals" / "results").glob("*.json"))
    require(result_files, f"{relative(eval_path)}: missing dated validation result")
    for result_path in result_files:
        result = load_json(result_path)
        require(result.get("skill") == skill_name, f"{relative(result_path)}: skill mismatch")
        require(
            result.get("status") in {"passed", "failed", "partial"},
            f"{relative(result_path)}: invalid status",
        )


def validate_plugin_interface(manifest_path: Path, manifest: dict, category: str) -> None:
    interface = manifest.get("interface")
    require(isinstance(interface, dict), f"{relative(manifest_path)}: missing interface")
    for field in REQUIRED_PLUGIN_INTERFACE_STRINGS:
        require(
            isinstance(interface.get(field), str) and interface[field].strip(),
            f"{relative(manifest_path)}: missing interface.{field}",
        )
    require(
        interface.get("category") == category,
        f"{relative(manifest_path)}: interface category differs from marketplace",
    )
    require(
        interface["websiteURL"].startswith("https://")
        and interface["privacyPolicyURL"].startswith("https://"),
        f"{relative(manifest_path)}: public URLs must use HTTPS",
    )
    capabilities = interface.get("capabilities")
    require(
        isinstance(capabilities, list)
        and capabilities
        and all(isinstance(value, str) and value.strip() for value in capabilities),
        f"{relative(manifest_path)}: capabilities must be a non-empty string array",
    )
    prompts = interface.get("defaultPrompt")
    require(
        isinstance(prompts, list)
        and 1 <= len(prompts) <= 3
        and all(isinstance(value, str) and value.strip() for value in prompts),
        f"{relative(manifest_path)}: defaultPrompt must contain one to three prompts",
    )
    require(
        HEX_COLOR_RE.fullmatch(str(interface.get("brandColor", ""))) is not None,
        f"{relative(manifest_path)}: brandColor must use #RRGGBB",
    )


def validate_skill(plugin_dir: Path, skill_md: Path, skill_names: set[str]) -> str:
    metadata = frontmatter(skill_md)
    skill_name = metadata.get("name")
    description = metadata.get("description", "").strip()
    require(skill_name == skill_md.parent.name, f"{relative(skill_md)}: name must match folder")
    require(NAME_RE.fullmatch(skill_name or "") is not None, f"{relative(skill_md)}: invalid name")
    require(skill_name not in skill_names, f"duplicate skill name: {skill_name}")
    require(80 <= len(description) <= 500, f"{relative(skill_md)}: description must be 80-500 characters")
    require("Do not use" in description, f"{relative(skill_md)}: description needs a Do not use boundary")
    require(
        f"${skill_name}" not in description,
        f"{relative(skill_md)}: keep invocation syntax out of the activation description",
    )

    text = skill_md.read_text(encoding="utf-8")
    require(MODEL_VERSION_RE.search(text) is None, f"{relative(skill_md)}: model version belongs in a reference")
    require("window.openai" not in text, f"{relative(skill_md)}: host API belongs in a reference")
    require("codex://" not in text, f"{relative(skill_md)}: host URI belongs in a reference")
    require(PERSONAL_PATH_RE.search(text) is None, f"{relative(skill_md)}: contains a personal absolute path")

    for reference in re.findall(r"`(references/[^`]+)`", text):
        target = skill_md.parent / reference
        require(target.is_file(), f"{relative(skill_md)}: missing referenced file {reference}")

    validate_agent_metadata(skill_md.parent)
    validate_eval(plugin_dir, skill_name or "")
    skill_names.add(skill_name or "")
    return skill_name or ""


def validate() -> tuple[int, int, int]:
    marketplace = load_json(MARKETPLACE_PATH)
    marketplace_name = marketplace.get("name")
    require(
        isinstance(marketplace_name, str) and NAME_RE.fullmatch(marketplace_name),
        "marketplace name must be lower-case kebab-case",
    )
    display_name = marketplace.get("interface", {}).get("displayName")
    require(isinstance(display_name, str) and display_name.strip(), "missing marketplace displayName")

    entries = marketplace.get("plugins")
    require(isinstance(entries, list) and entries, "marketplace must list at least one plugin")

    entry_names: set[str] = set()
    skill_names: set[str] = set()
    eval_count = 0

    for entry in entries:
        require(isinstance(entry, dict), "each marketplace plugin entry must be an object")
        name = entry.get("name")
        require(isinstance(name, str) and NAME_RE.fullmatch(name), f"invalid plugin name: {name!r}")
        require(name not in entry_names, f"duplicate marketplace plugin: {name}")
        entry_names.add(name)

        source = entry.get("source")
        expected_path = f"./plugins/{name}"
        require(
            source == {"source": "local", "path": expected_path},
            f"{name}: source must be local path {expected_path}",
        )
        policy = entry.get("policy", {})
        require(policy.get("installation") in INSTALL_POLICIES, f"{name}: invalid installation policy")
        require(policy.get("authentication") in AUTH_POLICIES, f"{name}: invalid authentication policy")
        category = entry.get("category")
        require(category in MARKETPLACE_CATEGORIES, f"{name}: unsupported marketplace category {category!r}")

        plugin_dir = ROOT / "plugins" / name
        manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
        manifest = load_json(manifest_path)
        require(manifest.get("name") == name, f"{name}: manifest name mismatch")
        version = str(manifest.get("version", ""))
        require(SEMVER_RE.fullmatch(version) is not None, f"{name}: invalid semver")
        require(
            isinstance(manifest.get("description"), str) and manifest["description"].strip(),
            f"{name}: missing description",
        )
        require(
            isinstance(manifest.get("author"), dict)
            and isinstance(manifest["author"].get("name"), str)
            and manifest["author"]["name"].strip(),
            f"{name}: missing author.name",
        )
        require(manifest.get("skills") == "./skills/", f"{name}: skills path must be ./skills/")
        require(manifest.get("license") == "MIT", f"{name}: license is not allowed by repository policy")
        validate_plugin_interface(manifest_path, manifest, category)

        skill_files = sorted((plugin_dir / "skills").glob("*/SKILL.md"))
        require(skill_files, f"{name}: plugin contains no skills")
        for skill_md in skill_files:
            skill_name = validate_skill(plugin_dir, skill_md, skill_names)
            if len(skill_files) == 1:
                require(skill_name == name, f"{name}: one-skill plugin must share the canonical skill name")
            eval_count += 1

        plugin_readme = plugin_dir / "README.md"
        require(plugin_readme.is_file(), f"{name}: missing plugin README")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        require(
            f"## {name} {version}" in changelog,
            f"{name}: changelog has no {version} release entry",
        )

    plugin_dirs = {
        path.name
        for path in (ROOT / "plugins").iterdir()
        if path.is_dir() and (path / ".codex-plugin" / "plugin.json").is_file()
    }
    require(plugin_dirs == entry_names, "stable plugin directories and marketplace entries differ")

    catalog_text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((ROOT / "catalog").glob("*.md"))
    )
    for name in entry_names:
        require(f"../plugins/{name}/" in catalog_text, f"{name}: missing category catalog link")

    unfinished_marker = "[" + "TODO:"
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        require(not path.is_symlink(), f"symbolic link is not allowed: {relative(path)}")
        if not path.is_file():
            continue
        raw = path.read_bytes()
        if b"\x00" in raw:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        require(unfinished_marker not in text, f"unfinished placeholder: {relative(path)}")
        require(PERSONAL_PATH_RE.search(text) is None, f"personal absolute path: {relative(path)}")
        require(EMAIL_RE.search(text) is None, f"email address is not allowed: {relative(path)}")
        for label, pattern in SENSITIVE_TEXT_PATTERNS.items():
            require(pattern.search(text) is None, f"{label} pattern found: {relative(path)}")

    return len(entry_names), len(skill_names), eval_count


def main() -> int:
    try:
        plugins, skills, evals = validate()
    except (OSError, ValidationError) as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Validated {plugins} plugin(s), {skills} skill(s), and {evals} golden request set(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
