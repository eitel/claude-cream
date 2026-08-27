#!/usr/bin/env python3
"""Validate theme structure, token mappings, contrast, and packaged artifact."""

from __future__ import annotations

import io
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent.parent
RESOURCES = ROOT / "src" / "main" / "resources"
PALETTE = ROOT / "palette" / "claude-cream.json"
PLUGIN_XML = RESOURCES / "META-INF" / "plugin.xml"
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")
SCHEME_COLOR = re.compile(r"^[0-9a-fA-F]{1,8}$")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted(
        (relative_luminance(foreground), relative_luminance(background)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"{path.relative_to(ROOT)}: {error}")
    if not isinstance(value, dict):
        fail(f"{path.relative_to(ROOT)}: root must be an object")
    return value


def flatten_ui(value: object, prefix: str = "") -> dict[str, object]:
    flattened: dict[str, object] = {}
    if not isinstance(value, dict):
        return flattened
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(child, dict):
            flattened.update(flatten_ui(child, path))
        else:
            flattened[path] = child
    return flattened


def validate_plugin_descriptor() -> tuple[str, list[Path]]:
    try:
        root = ElementTree.parse(PLUGIN_XML).getroot()
    except (OSError, ElementTree.ParseError) as error:
        fail(f"src/main/resources/META-INF/plugin.xml: {error}")

    plugin_id = root.findtext("id")
    version = root.findtext("version")
    idea_version = root.find("idea-version")
    if plugin_id != "io.github.eitel.claudecream.idea":
        fail("plugin.xml: unexpected or missing stable plugin id")
    if not version:
        fail("plugin.xml: missing version")
    if idea_version is None or idea_version.get("since-build") != "243":
        fail("plugin.xml: since-build must be 243 (IntelliJ Platform 2024.3)")
    if idea_version.get("until-build"):
        fail("plugin.xml: omit until-build to retain 2026.x compatibility")

    providers = root.findall("./extensions/themeProvider")
    if len(providers) != 2:
        fail("plugin.xml: exactly two themeProvider entries are required")
    paths: list[Path] = []
    ids: set[str] = set()
    for provider in providers:
        provider_id = provider.get("id")
        resource = provider.get("path")
        if not provider_id or provider_id in ids or not resource:
            fail("plugin.xml: themeProvider ids and paths must be unique and non-empty")
        ids.add(provider_id)
        path = RESOURCES / resource.lstrip("/")
        if not path.is_file():
            fail(f"plugin.xml: missing theme resource {resource}")
        paths.append(path)
    return version.strip(), paths


def validate_theme(path: Path, mode: str, tokens: dict[str, object]) -> Path:
    theme = load_json(path)
    expected_dark = mode == "dark"
    if theme.get("dark") is not expected_dark:
        fail(f"{path.name}: dark flag does not match {mode}")
    if theme.get("name") != f"Claude Cream {mode.title()}":
        fail(f"{path.name}: unexpected theme name")

    palette = theme.get("colors")
    if not isinstance(palette, dict) or len(palette) < 20:
        fail(f"{path.name}: expected at least 20 named palette colors")
    for key, color in palette.items():
        if not isinstance(color, str) or not HEX_COLOR.fullmatch(color):
            fail(f"{path.name}: colors.{key} is not #RRGGBB or #RRGGBBAA")

    ui_config = theme.get("ui")
    if not isinstance(ui_config, dict):
        fail(f"{path.name}: ui must be an object")
    ui = flatten_ui(ui_config)
    if len(ui) < 100:
        fail(f"{path.name}: only {len(ui)} UI overrides; expected comprehensive coverage")
    unknown_references = {
        value
        for value in ui.values()
        if isinstance(value, str)
        and value.startswith("Cream")
        and value not in palette
    }
    if unknown_references:
        fail(f"{path.name}: unknown palette references {sorted(unknown_references)}")

    if mode == "light":
        main_toolbar = ui_config.get("MainToolbar")
        if not isinstance(main_toolbar, dict):
            fail(f"{path.name}: MainToolbar must be an object")
        expected_toolbar = {
            "background": "CreamCanvas",
            "foreground": "CreamBodyStrong",
        }
        for key, expected in expected_toolbar.items():
            if main_toolbar.get(key) != expected:
                fail(f"{path.name}: MainToolbar.{key} must be {expected}")

        icon_source = "/expui/general/moreVertical_stroke.svg"
        icon_target = "/expui/general/moreVertical.svg"
        icons = theme.get("icons")
        if not isinstance(icons, dict) or icons.get(icon_source) != icon_target:
            fail(
                f"{path.name}: the white main-toolbar overflow icon must map to "
                f"{icon_target}"
            )

        toolbar_foreground = palette[main_toolbar["foreground"]]
        toolbar_background = palette[main_toolbar["background"]]
        ratio = contrast(toolbar_foreground, toolbar_background)
        if ratio < 4.5:
            fail(
                f"{path.name}: main toolbar foreground contrast "
                f"{ratio:.2f}:1 is below 4.5:1"
            )

    source_colors = tokens["colors"][mode]
    expected_palette = {
        "CreamCanvas": source_colors["canvas"],
        "CreamBody": source_colors["body"],
        "CreamAccent": source_colors["primary"],
        "CreamBorder": source_colors["hairline"],
        "CreamTeal": source_colors["accent-teal"],
        "CreamGreen": source_colors["success"],
        "CreamError": source_colors["error"],
    }
    for name, expected in expected_palette.items():
        if palette.get(name) != expected:
            fail(f"{path.name}: {name} drifted from upstream token {expected}")

    editor_scheme = theme.get("editorScheme")
    if not isinstance(editor_scheme, str):
        fail(f"{path.name}: missing editorScheme")
    scheme_path = RESOURCES / editor_scheme.lstrip("/")
    if not scheme_path.is_file():
        fail(f"{path.name}: missing editor scheme {editor_scheme}")
    return scheme_path


def attribute_foreground(attributes: ElementTree.Element, name: str) -> str | None:
    option = attributes.find(f"./option[@name='{name}']/value/option[@name='FOREGROUND']")
    return option.get("value") if option is not None else None


def validate_scheme(path: Path, mode: str, tokens: dict[str, object]) -> None:
    try:
        root = ElementTree.parse(path).getroot()
    except (OSError, ElementTree.ParseError) as error:
        fail(f"{path.relative_to(ROOT)}: {error}")
    if root.tag != "scheme" or root.get("version") != "142":
        fail(f"{path.name}: expected IntelliJ color scheme version 142")
    if root.get("name") != f"Claude Cream {mode.title()}":
        fail(f"{path.name}: scheme name does not match theme")

    colors = root.find("colors")
    attributes = root.find("attributes")
    if colors is None or attributes is None:
        fail(f"{path.name}: missing colors or attributes")
    for option in colors.findall("option"):
        value = option.get("value", "")
        if value and not SCHEME_COLOR.fullmatch(value):
            fail(f"{path.name}: invalid scheme color {option.get('name')}={value}")

    required_attributes = {
        "TEXT",
        "DEFAULT_IDENTIFIER",
        "DEFAULT_KEYWORD",
        "DEFAULT_STRING",
        "DEFAULT_NUMBER",
        "DEFAULT_LINE_COMMENT",
        "DEFAULT_FUNCTION_CALL",
        "DEFAULT_CLASS_REFERENCE",
        "ERRORS_ATTRIBUTES",
        "WARNING_ATTRIBUTES",
        "DIFF_INSERTED",
        "DIFF_DELETED",
        "DIFF_MODIFIED",
        "CONSOLE_NORMAL_OUTPUT",
    }
    actual_attributes = {option.get("name") for option in attributes.findall("option")}
    missing = required_attributes - actual_attributes
    if missing:
        fail(f"{path.name}: missing editor attributes {sorted(missing)}")

    syntax = tokens["syntax"][mode]
    mappings = {
        "DEFAULT_KEYWORD": syntax["keyword"],
        "DEFAULT_STRING": syntax["string"],
        "DEFAULT_LINE_COMMENT": syntax["comment"],
        "DEFAULT_FUNCTION_CALL": syntax["function"],
        "DEFAULT_CLASS_REFERENCE": syntax["type"],
        "DEFAULT_IDENTIFIER": syntax["variable"],
        "DEFAULT_NUMBER": syntax["number"],
        "DEFAULT_OPERATION_SIGN": syntax["operator"],
        "DEFAULT_BRACES": syntax["punctuation"],
        "DEFAULT_TAG": syntax["tag"],
        "DEFAULT_ATTRIBUTE": syntax["attribute"],
    }
    for attribute, expected in mappings.items():
        actual = attribute_foreground(attributes, attribute)
        if actual != expected.lstrip("#"):
            fail(f"{path.name}: {attribute}={actual}, expected {expected}")

    editor = tokens["editor"][mode]
    checks = {
        "editor foreground": (editor["foreground-default"], editor["canvas-default"]),
        "comment": (syntax["comment"], editor["canvas-default"]),
    }
    for label, (foreground, background) in checks.items():
        ratio = contrast(foreground, background)
        if ratio < 4.5:
            fail(f"{path.name}: {label} contrast {ratio:.2f}:1 is below 4.5:1")


def validate_artifact(version: str) -> None:
    artifact = ROOT / "dist" / f"claude-cream-idea-{version}.zip"
    if not artifact.is_file():
        fail(f"missing built artifact {artifact.relative_to(ROOT)}; run scripts/build.py")
    with zipfile.ZipFile(artifact) as plugin_zip:
        names = plugin_zip.namelist()
        expected_jar = f"claude-cream-idea/lib/claude-cream-idea-{version}.jar"
        if names != [expected_jar]:
            fail(f"{artifact.name}: unexpected plugin ZIP layout {names}")
        jar_data = plugin_zip.read(expected_jar)
    with zipfile.ZipFile(io.BytesIO(jar_data)) as plugin_jar:
        names = set(plugin_jar.namelist())
        required = {
            "META-INF/MANIFEST.MF",
            "META-INF/plugin.xml",
            "META-INF/pluginIcon.svg",
            "META-INF/pluginIcon_dark.svg",
            "META-INF/LICENSE.txt",
            "META-INF/NOTICE.txt",
            "themes/ClaudeCreamLight.theme.json",
            "themes/ClaudeCreamDark.theme.json",
            "themes/ClaudeCreamLight.xml",
            "themes/ClaudeCreamDark.xml",
        }
        missing = required - names
        if missing:
            fail(f"plugin JAR is missing {sorted(missing)}")
        ElementTree.fromstring(plugin_jar.read("META-INF/plugin.xml"))
        json.loads(plugin_jar.read("themes/ClaudeCreamLight.theme.json"))
        json.loads(plugin_jar.read("themes/ClaudeCreamDark.theme.json"))


def main() -> None:
    tokens = load_json(PALETTE)
    version, theme_paths = validate_plugin_descriptor()
    by_mode = {
        "dark" if "Dark" in path.name else "light": path
        for path in theme_paths
    }
    if set(by_mode) != {"light", "dark"}:
        fail("plugin.xml: expected one Light and one Dark theme")
    for mode in ("light", "dark"):
        scheme_path = validate_theme(by_mode[mode], mode, tokens)
        validate_scheme(scheme_path, mode, tokens)
    validate_artifact(version)
    print("Claude Cream IDEA validation passed")


if __name__ == "__main__":
    main()
