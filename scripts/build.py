#!/usr/bin/env python3
"""Build a deterministic, resource-only IntelliJ Platform plugin ZIP."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent.parent
RESOURCES = ROOT / "src" / "main" / "resources"
BUILD = ROOT / "build"
DIST = ROOT / "dist"
PLUGIN_SLUG = "claude-cream-idea"
ZIP_TIMESTAMP = (2026, 8, 26, 0, 0, 0)


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


def add_bytes(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    archive.writestr(zip_info(name), data)


def plugin_version() -> str:
    descriptor = ElementTree.parse(RESOURCES / "META-INF" / "plugin.xml").getroot()
    version = descriptor.findtext("version")
    if not version:
        raise RuntimeError("META-INF/plugin.xml is missing <version>")
    return version.strip()


def build_jar() -> tuple[Path, bytes]:
    version = plugin_version()
    jar_path = BUILD / "libs" / f"{PLUGIN_SLUG}-{version}.jar"
    jar_path.parent.mkdir(parents=True, exist_ok=True)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        add_bytes(
            archive,
            "META-INF/MANIFEST.MF",
            b"Manifest-Version: 1.0\nCreated-By: Claude Cream build.py\n\n",
        )
        for path in sorted(RESOURCES.rglob("*")):
            if path.is_file():
                add_bytes(archive, path.relative_to(RESOURCES).as_posix(), path.read_bytes())

    jar_bytes = buffer.getvalue()
    jar_path.write_bytes(jar_bytes)
    return jar_path, jar_bytes


def build_plugin() -> Path:
    jar_path, jar_bytes = build_jar()
    version = plugin_version()
    artifact = DIST / f"{PLUGIN_SLUG}-{version}.zip"
    artifact.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(artifact, "w") as archive:
        add_bytes(
            archive,
            f"{PLUGIN_SLUG}/lib/{jar_path.name}",
            jar_bytes,
        )

    return artifact


if __name__ == "__main__":
    output = build_plugin()
    print(output.relative_to(ROOT))
