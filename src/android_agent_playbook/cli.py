"""android-agent-playbook: AI agent rules and commands for Android projects.

Zero dependencies, Python 3.8+. Detects the Gradle/Android stack of a project
and writes AGENTS.md, CLAUDE.md, Cursor/Copilot pointers and agent playbooks
inside marker blocks, so re-running is safe and the user's own text is kept.
"""

import argparse
import difflib
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

from . import __version__

MARK = "android-agent-playbook"
START = "<!-- %s:start -->" % MARK
END = "<!-- %s:end -->" % MARK
TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

PRESETS = ("compose", "views-compose", "kmp")
AGENTS = ("claude", "codex", "cursor", "copilot")
SKILLS = ("add-screen", "add-feature-module", "migrate-to-compose", "write-tests", "fix-build")
ARG_HINTS = {
    "add-screen": "<screen name and what it shows>",
    "add-feature-module": "<module name, e.g. settings>",
    "migrate-to-compose": "<Fragment, Activity or layout to migrate>",
    "write-tests": "<class, file or behavior to test>",
    "fix-build": "[failing command or error]",
}
SKIP_DIRS = {".git", ".gradle", "build", ".idea", "node_modules", ".kotlin", ".cxx", ".fleet"}


# --------------------------------------------------------------------------- #
# Detection
# --------------------------------------------------------------------------- #

def _read(path):
    # type: (str) -> str
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _first_existing(root, names):
    # type: (str, Tuple[str, ...]) -> Optional[str]
    for name in names:
        path = os.path.join(root, name)
        if os.path.isfile(path):
            return path
    return None


def _strip_comments(text):
    # type: (str) -> str
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$|\s//\s.*$", "", text)


def parse_modules(settings_text):
    # type: (str) -> List[str]
    """Return Gradle project paths from include(...) statements, in file order."""
    text = _strip_comments(settings_text)
    found = []  # type: List[str]
    for match in re.finditer(r"\binclude\b[ \t]*(?:\((.*?)\)|([^\n]+))", text, flags=re.S):
        chunk = match.group(1) if match.group(1) is not None else match.group(2)
        for name in re.findall(r"[\"']([^\"']+)[\"']", chunk):
            name = name if name.startswith(":") else ":" + name
            if name not in found:
                found.append(name)
    return found


def classify_module(build_text):
    # type: (str) -> str
    t = _strip_comments(build_text)
    if re.search(r"kotlin\(\"multiplatform\"\)|kotlin[.\-]?multiplatform", t, re.I):
        return "kmp"
    if re.search(r"com\.android\.application|android[.\-]application|androidApplication", t):
        return "application"
    if re.search(r"com\.android\.library|android[.\-]library|androidLibrary|android[.\-]feature", t):
        return "library"
    if re.search(r"com\.android\.test|android[.\-]test\b", t):
        return "android-test"
    if re.search(r"kotlin\(\"jvm\"\)|org\.jetbrains\.kotlin\.jvm|kotlin[.\-]jvm|java-library|jvm[.\-]library", t):
        return "jvm"
    return "unknown"


def _module_dir(root, path):
    # type: (str, str) -> str
    return os.path.join(root, *[p for p in path.split(":") if p])


def _walk_files(base, exts, limit=400):
    # type: (str, Tuple[str, ...], int) -> List[str]
    out = []  # type: List[str]
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(exts):
                out.append(os.path.join(dirpath, name))
                if len(out) >= limit:
                    return out
    return out


def _has_layouts(module_dir):
    # type: (str) -> bool
    src = os.path.join(module_dir, "src")
    if not os.path.isdir(src):
        return False
    for source_set in os.listdir(src):
        layout = os.path.join(src, source_set, "res", "layout")
        if os.path.isdir(layout) and any(n.endswith(".xml") for n in os.listdir(layout)):
            return True
    return False


FEATURE_PATTERNS = {
    "compose": r"compose\s*[=(]\s*true|plugin\.compose|plugin-compose|androidx\.compose|compose[-.]bom|jetbrains\.compose|compose-compiler",
    "compose_multiplatform": r"org\.jetbrains\.compose|jetbrains-compose|compose\.multiplatform|composeMultiplatform",
    "view_binding": r"viewBinding\s*[=(]?\s*true|dataBinding\s*[=(]?\s*true|viewBinding\s*\{",
    "hilt": r"hilt",
    "koin": r"koin",
    "room": r"androidx[.:]room|room[-_.]runtime|room[-_.]compiler|androidx-room",
    "sqldelight": r"sqldelight",
    "ksp": r"\bksp\b|devtools\.ksp",
    "kapt": r"\bkapt\b|kotlin-kapt",
    "coroutines": r"kotlinx[-.]coroutines",
    "navigation_compose": r"navigation[-.]compose",
    "navigation_fragment": r"navigation[-.]fragment",
    "retrofit": r"retrofit",
    "ktor": r"ktor",
    "serialization": r"kotlinx[-.]serialization|plugin\.serialization",
}
TEST_PATTERNS = (
    ("JUnit 5", r"junit[-.]jupiter|junit5|de\.mannodermaus"),
    ("JUnit 4", r"junit:junit|[\"']junit[\"']|junit4|\bjunit\s*=|androidx[.\-]test[.\-]ext[.\-]junit"),
    ("kotlin.test", r"kotlin[(\"'.\-]+test|kotlin-test"),
    ("MockK", r"mockk"),
    ("Mockito", r"mockito"),
    ("Turbine", r"turbine"),
    ("Truth", r"google\.truth|\btruth\b"),
    ("Kotest", r"kotest"),
    ("Robolectric", r"robolectric"),
    ("Compose UI test", r"ui[-.]test[-.]junit4|compose[-.]ui[-.]test|uiTestJunit4"),
    ("Espresso", r"espresso"),
    ("coroutines-test", r"coroutines[-.]test"),
    ("Roborazzi/Paparazzi", r"roborazzi|paparazzi"),
)
LINT_PATTERNS = (
    ("ktlint", r"ktlint"),
    ("detekt", r"detekt"),
    ("spotless", r"spotless"),
)


def _cap(name):
    # type: (str) -> str
    return name[:1].upper() + name[1:]


def _braced(text, start):
    # type: (str, int) -> Tuple[str, int]
    """Return the body of the {...} block whose opening brace is at or after `start`."""
    i = text.find("{", start)
    if i < 0:
        return "", start
    depth, j = 1, i + 1
    while j < len(text) and depth:
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
        j += 1
    return text[i + 1:j - 1], j


FLAVOR_ENTRY = re.compile(
    r"(?:\b(?:create|register|maybeCreate|getByName)\s*\(\s*[\"']([^\"']+)[\"']\s*\)"
    r"|(?m:^[ \t]*([A-Za-z_]\w*)))\s*\{")
NOT_FLAVORS = {"all", "configureEach", "forEach", "each", "named", "matching", "withType"}
PREFERRED_FLAVORS = ("dev", "develop", "development", "demo", "staging", "stage", "qa", "internal", "mock")


def parse_flavors(build_text):
    # type: (str) -> Dict
    """Return {"dimensions": [...], "flavors": [{"name", "dimension", "default"}], "variant": "devDebug"}."""
    text = _strip_comments(build_text)
    dimensions = []  # type: List[str]
    for line in re.findall(r"flavorDimensions[^\n]*", text):
        for d in re.findall(r"[\"']([^\"']+)[\"']", line):
            if d not in dimensions:
                dimensions.append(d)
    flavors = []  # type: List[Dict]
    m = re.search(r"\bproductFlavors\s*\{", text)
    if m:
        body, _ = _braced(text, m.start())
        for entry in FLAVOR_ENTRY.finditer(body):
            name = entry.group(1) or entry.group(2)
            if name in NOT_FLAVORS or body[:entry.start()].count("{") != body[:entry.start()].count("}"):
                continue
            sub, _ = _braced(body, entry.end() - 1)
            dim = re.search(r"dimension\s*[=(]?\s*[\"']([^\"']+)[\"']", sub)
            default = re.search(r"isDefault\s*(?:=\s*true|\.set\(\s*true\s*\)|\(\s*true\s*\)|[ \t]+true)", sub)
            flavors.append({"name": name, "dimension": dim.group(1) if dim else None,
                            "default": bool(default)})
    variant = "debug"
    if flavors:
        if not dimensions:
            dimensions = []
            for f in flavors:
                if f["dimension"] not in dimensions:
                    dimensions.append(f["dimension"])
        chosen = []
        for dim in dimensions:
            group = [f for f in flavors if f["dimension"] == dim or (len(dimensions) == 1 and f["dimension"] is None)]
            if not group:
                continue
            pick = next((f for f in group if f["default"]), None)
            if pick is None:
                for pref in PREFERRED_FLAVORS:
                    pick = next((f for f in group if f["name"].lower() == pref), None)
                    if pick:
                        break
            chosen.append((pick or group[0])["name"])
        if chosen:
            variant = chosen[0] + "".join(_cap(c) for c in chosen[1:]) + "Debug"
        dimensions = [d for d in dimensions if d is not None]
    return {"dimensions": dimensions, "flavors": flavors, "variant": variant}


def _catalog_versions(catalog_text):
    # type: (str) -> Dict[str, str]
    m = re.search(r"(?ms)^\[versions\]\s*$(.*?)(?=^\[|\Z)", catalog_text)
    if not m:
        return {}
    return dict(re.findall(r"(?m)^\s*([A-Za-z0-9_.\-]+)\s*=\s*[\"']([^\"']+)[\"']", m.group(1)))


def _resolve_number(expr, versions):
    # type: (str, Dict[str, str]) -> Optional[str]
    expr = expr.strip()
    num = re.match(r"(\d+)", expr)
    if num:
        return num.group(1)
    ref = re.search(r"libs\.versions\.([\w.]+?)\.get\(", expr)
    if ref:
        wanted = ref.group(1).lower()
        for key, value in versions.items():
            if re.sub(r"[-_.]", ".", key).lower() == wanted and value.isdigit():
                return value
    return None


def _sdk_level(texts, names, versions):
    # type: (List[str], Tuple[str, ...], Dict[str, str]) -> Optional[str]
    pattern = r"\b(?:%s)\b\s*(?:=|\(|[ \t])\s*([^\n)]+)" % "|".join(names)
    for text in texts:
        for expr in re.findall(pattern, _strip_comments(text)):
            value = _resolve_number(expr, versions)
            if value:
                return value
    for key, value in versions.items():
        flat = re.sub(r"[-_.]", "", key).lower()
        if value.isdigit() and any(flat.endswith(n.replace("Version", "").lower()) for n in names):
            return value
    return None


def _catalog_version(versions, keys):
    # type: (Dict[str, str], Tuple[str, ...]) -> Optional[str]
    norm = {re.sub(r"[-_.]", "", k).lower(): v for k, v in versions.items()}
    for key in keys:
        if key in norm:
            return norm[key]
    return None


def _first_group(pattern, text):
    # type: (str, str) -> Optional[str]
    m = re.search(pattern, text)
    return m.group(1) if m else None


def _catalog_plugin_version(catalog_text, versions, plugin_ids):
    # type: (str, Dict[str, str], Tuple[str, ...]) -> Optional[str]
    for pid in plugin_ids:
        line = _first_group(r"(?m)^[^\n#]*id\s*=\s*[\"']%s[\"']([^\n]*)$" % re.escape(pid), catalog_text)
        if line is None:
            continue
        inline = _first_group(r"version\s*=\s*[\"']([^\"']+)[\"']", line)
        if inline:
            return inline
        ref = _first_group(r"version\.ref\s*=\s*[\"']([^\"']+)[\"']", line)
        if ref and ref in versions:
            return versions[ref]
    return None


def detect_build_facts(root, texts, catalog_text):
    # type: (str, List[str], str) -> Dict
    versions = _catalog_versions(catalog_text)
    blob = "\n".join(texts + [catalog_text])
    facts = {
        "min_sdk": _sdk_level(texts, ("minSdk", "minSdkVersion"), versions),
        "target_sdk": _sdk_level(texts, ("targetSdk", "targetSdkVersion"), versions),
        "compile_sdk": _sdk_level(texts, ("compileSdk", "compileSdkVersion"), versions),
        "jdk": None, "agp": None, "kotlin": None, "gradle": None, "compose_bom": None,
    }  # type: Dict
    jdk = (re.search(r"jvmToolchain\s*\(\s*(\d+)", blob)
           or re.search(r"JavaLanguageVersion\.of\(\s*(\d+)", blob)
           or re.search(r"JavaVersion\.VERSION_(?:1_)?(\d+)", blob)
           or re.search(r"JvmTarget\.JVM_(?:1_)?(\d+)", blob)
           or re.search(r"jvmTarget\s*=\s*[\"'](?:1\.)?(\d+)", blob))
    if jdk:
        facts["jdk"] = jdk.group(1)
    facts["agp"] = (
        _catalog_version(versions, ("agp", "androidgradleplugin", "androidgradle", "androidplugin", "androidtoolsbuild"))
        or _catalog_plugin_version(catalog_text, versions, ("com.android.application", "com.android.library"))
        or _first_group(r"(?:com\.android\.tools\.build:gradle:|[\"']com\.android\.(?:application|library)[\"']\s*\)?\s*version\s*[\"'])([\d.]+)", blob))
    facts["kotlin"] = (
        _catalog_version(versions, ("kotlin", "kotlinversion", "kotlinlang"))
        or _catalog_plugin_version(catalog_text, versions, ("org.jetbrains.kotlin.android", "org.jetbrains.kotlin.multiplatform", "org.jetbrains.kotlin.jvm"))
        or _first_group(r"(?:kotlin-gradle-plugin:|kotlin\([\"'](?:android|jvm|multiplatform)[\"']\)\s*version\s*[\"']|[\"']org\.jetbrains\.kotlin\.(?:android|jvm|multiplatform)[\"']\s*\)?\s*version\s*[\"'])([\w.\-]+)", blob))
    facts["compose_bom"] = (
        _catalog_version(versions, ("composebom", "androidxcomposebom"))
        or _first_group(r"compose-bom:([\d.]+)", blob))
    wrapper = _read(os.path.join(root, "gradle", "wrapper", "gradle-wrapper.properties"))
    gm = re.search(r"gradle-([\d.]+(?:-rc-\d+)?)-(?:bin|all)\.zip", wrapper)
    if gm:
        facts["gradle"] = gm.group(1)
    return facts


def detect(root):
    # type: (str) -> Dict
    root = os.path.abspath(root)
    settings = _first_existing(root, ("settings.gradle.kts", "settings.gradle"))
    root_build = _first_existing(root, ("build.gradle.kts", "build.gradle"))
    info = {
        "root": root,
        "is_gradle": bool(settings or root_build),
        "settings_file": os.path.basename(settings) if settings else "settings.gradle.kts",
        "dsl": None,
        "project_name": os.path.basename(root),
        "gradle": "./gradlew" if os.path.isfile(os.path.join(root, "gradlew")) else "gradle",
        "version_catalog": os.path.isfile(os.path.join(root, "gradle", "libs.versions.toml")),
        "build_logic": None,
        "modules": [],
        "app_module": None,
        "features": {},
        "tests": [],
        "lint_tools": [],
        "has_layouts": False,
    }  # type: Dict
    if settings:
        info["dsl"] = "kts" if settings.endswith(".kts") else "groovy"
    elif root_build:
        info["dsl"] = "kts" if root_build.endswith(".kts") else "groovy"

    settings_text = _read(settings) if settings else ""
    m = re.search(r"rootProject\.name\s*=\s*[\"']([^\"']+)[\"']", settings_text)
    if m:
        info["project_name"] = m.group(1)

    for candidate in ("build-logic", "buildSrc", "convention-plugins", "gradle/build-logic"):
        if os.path.isdir(os.path.join(root, candidate)):
            info["build_logic"] = candidate
            break

    module_paths = parse_modules(settings_text)
    if not module_paths and os.path.isdir(os.path.join(root, "app")):
        module_paths = [":app"]

    corpus = [settings_text, _read(root_build) if root_build else ""]
    catalog_text = _read(os.path.join(root, "gradle", "libs.versions.toml")) if info["version_catalog"] else ""
    corpus.append(catalog_text)
    logic_texts = []  # type: List[str]
    if info["build_logic"]:
        for path in _walk_files(os.path.join(root, info["build_logic"]), (".kt", ".kts", ".gradle", ".toml")):
            logic_texts.append(_read(path))
    corpus += logic_texts
    module_texts = {}  # type: Dict[str, str]

    for path in module_paths:
        mdir = _module_dir(root, path)
        build = _first_existing(mdir, ("build.gradle.kts", "build.gradle"))
        text = _read(build) if build else ""
        corpus.append(text)
        module_texts[path] = text
        mtype = classify_module(text) if build else "missing"
        if mtype == "unknown" and path.split(":")[-1] == "app":
            mtype = "application"
        layouts = _has_layouts(mdir)
        info["has_layouts"] = info["has_layouts"] or layouts
        flavors = parse_flavors(text) if mtype in ("application", "library") else {"dimensions": [], "flavors": [], "variant": "debug"}
        info["modules"].append({
            "path": path,
            "dir": os.path.relpath(mdir, root),
            "type": mtype,
            "has_layouts": layouts,
            "flavors": [f["name"] for f in flavors["flavors"]],
            "flavor_dimensions": flavors["dimensions"],
            "variant": flavors["variant"],
        })

    apps = [m["path"] for m in info["modules"] if m["type"] == "application"]
    if ":app" in apps:
        info["app_module"] = ":app"
    elif apps:
        info["app_module"] = apps[0]

    app_text = module_texts.get(info["app_module"] or "", "")
    other_texts = [t for p, t in module_texts.items() if p != info["app_module"]]
    info["build"] = detect_build_facts(root, [app_text] + logic_texts + other_texts + [corpus[1]], catalog_text)
    app_entry = next((m for m in info["modules"] if m["path"] == info["app_module"]), None)
    info["variant"] = app_entry["variant"] if app_entry else "debug"
    info["flavors_in_build_logic"] = bool(re.search(r"productFlavors|flavorDimensions", "\n".join(logic_texts))) and not (app_entry and app_entry["flavors"])

    blob = "\n".join(corpus)
    features = {}
    for key, pattern in FEATURE_PATTERNS.items():
        features[key] = bool(re.search(pattern, blob, re.I))
    features["kmp"] = any(m["type"] == "kmp" for m in info["modules"]) or bool(
        re.search(r"kotlin\(\"multiplatform\"\)|kotlin[.\-]multiplatform", blob))
    features["views"] = info["has_layouts"] or features["view_binding"]
    features["android"] = bool(re.search(r"com\.android\.|android[.\-](application|library)|androidTarget|androidLibrary", blob))
    info["features"] = features
    info["tests"] = [name for name, pat in TEST_PATTERNS if re.search(pat, blob, re.I)]
    info["lint_tools"] = [name for name, pat in LINT_PATTERNS if re.search(pat, blob, re.I)]
    info["preset"] = suggest_preset(info)
    return info


def suggest_preset(info):
    # type: (Dict) -> str
    f = info["features"]
    if f.get("kmp"):
        return "kmp"
    if f.get("views"):
        return "views-compose"
    return "compose"


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

def _template(*parts):
    # type: (str) -> str
    return _read(os.path.join(TEMPLATES, *parts))


def split_frontmatter(text):
    # type: (str) -> Tuple[str, str]
    m = re.match(r"---\n.*?\n---\n", text, flags=re.S)
    if not m:
        return "", text
    return m.group(0), text[m.end():]


def frontmatter_value(frontmatter, key):
    # type: (str, str) -> str
    m = re.search(r"(?m)^%s:\s*(.+)$" % re.escape(key), frontmatter)
    return m.group(1).strip() if m else ""


def _module(info, path):
    # type: (Dict, Optional[str]) -> Optional[Dict]
    return next((m for m in info["modules"] if m["path"] == path), None)


def module_test_task(module):
    # type: (Optional[Dict]) -> str
    if module is None:
        return "testDebugUnitTest"
    if module["type"] == "kmp":
        return "allTests"
    if module["type"] == "jvm":
        return "test"
    return "test%sUnitTest" % _cap(module.get("variant") or "debug")


def commands(info):
    # type: (Dict) -> Dict[str, str]
    g = info["gradle"]
    app = info["app_module"]
    f = info["features"]
    v = _cap(info.get("variant") or "debug")
    cmds = {}  # type: Dict[str, str]
    cmds["build"] = "%s %s:assemble%s" % (g, app, v) if app else "%s assemble" % g
    if f.get("kmp"):
        cmds["test"] = "%s allTests" % g
    else:
        android = [m for m in info["modules"] if m["type"] in ("application", "library")]
        flavored = [m for m in android if m.get("variant", "debug") != "debug"]
        parts = ["%s:%s" % (m["path"], module_test_task(m)) for m in flavored]
        if len(flavored) < len(android) or not android:
            parts.append("testDebugUnitTest")
        cmds["test"] = "%s %s" % (g, " ".join(parts))
    lint = ["%s %s:lint%s" % (g, app, v) if app else "%s lint" % g]
    if "ktlint" in info["lint_tools"]:
        lint.append("%s ktlintCheck" % g)
    if "detekt" in info["lint_tools"]:
        lint.append("%s detekt" % g)
    if "spotless" in info["lint_tools"]:
        lint.append("%s spotlessCheck" % g)
    cmds["lint"] = " && ".join(lint)
    fmt = []
    if "spotless" in info["lint_tools"]:
        fmt.append("%s spotlessApply" % g)
    if "ktlint" in info["lint_tools"]:
        fmt.append("%s ktlintFormat" % g)
    if fmt:
        cmds["format"] = " && ".join(fmt)
    if app and f.get("android"):
        cmds["instrumented"] = "%s %s:connected%sAndroidTest" % (g, app, v)
    return cmds


def _example_module(info):
    # type: (Dict) -> str
    for m in info["modules"]:
        if m["path"] != info["app_module"] and m["type"] in ("library", "kmp"):
            return m["path"]
    return info["app_module"] or ":app"


def render_context(info, preset):
    # type: (Dict, str) -> Dict[str, str]
    f = info["features"]
    cmds = commands(info)
    g = info["gradle"]

    # Project map
    type_labels = {
        "application": "Android app", "library": "Android library", "kmp": "Kotlin Multiplatform",
        "jvm": "JVM/Kotlin library", "android-test": "Android test module",
        "unknown": "module", "missing": "no build file found",
    }
    if info["modules"]:
        rows = ["- `%s` (`%s/`): %s" % (m["path"], m["dir"], type_labels.get(m["type"], m["type"]))
                for m in info["modules"]]
        project_map = "\n".join(rows)
    else:
        project_map = "- Single-module project. TODO: describe the source layout."
    if info["build_logic"]:
        project_map += "\n- `%s/`: convention plugins shared by the modules" % info["build_logic"]
    project_map += "\n\nTODO: add one line per module describing what it owns, so agents put code in the right place."

    # Stack
    stack = []
    ui = []
    if f.get("compose"):
        ui.append("Compose Multiplatform" if f.get("compose_multiplatform") else "Jetpack Compose")
    if f.get("views"):
        ui.append("XML Views" + (" with View Binding" if f.get("view_binding") else ""))
    stack.append("- UI: %s" % (" + ".join(ui) if ui else "TODO"))
    if f.get("kmp"):
        stack.append("- Kotlin Multiplatform (shared code in `commonMain`)")
    di = "Hilt" if f.get("hilt") else "Koin" if f.get("koin") else None
    stack.append("- DI: %s" % (di or "constructor injection, no DI framework detected"))
    if f.get("coroutines"):
        stack.append("- Async: Kotlin coroutines and Flow")
    data = [n for n, k in (("Room", "room"), ("SQLDelight", "sqldelight"), ("Retrofit", "retrofit"),
                           ("Ktor", "ktor"), ("kotlinx.serialization", "serialization")) if f.get(k)]
    if data:
        stack.append("- Data: %s" % ", ".join(data))
    if f.get("navigation_compose") or f.get("navigation_fragment"):
        stack.append("- Navigation: %s" % ("Navigation Compose" if f.get("navigation_compose") else "Navigation component (Fragments)"))
    b = info.get("build") or {}
    sdk = ", ".join("%s %s" % (label, b[key]) for label, key in (("minSdk", "min_sdk"), ("targetSdk", "target_sdk"), ("compileSdk", "compile_sdk")) if b.get(key))
    if sdk:
        stack.append("- Android: %s%s" % (sdk, ". Guard APIs above minSdk with `Build.VERSION.SDK_INT` checks" if b.get("min_sdk") else ""))
    tools = ", ".join("%s %s" % (label, b[key]) for label, key in (("Gradle", "gradle"), ("AGP", "agp"), ("Kotlin", "kotlin"), ("JDK", "jdk"), ("Compose BOM", "compose_bom")) if b.get(key))
    if tools:
        stack.append("- Toolchain: %s" % tools)
    stack.append("- Build: Gradle %s DSL%s%s" % (
        "Kotlin" if info["dsl"] == "kts" else "Groovy",
        ", version catalog" if info["version_catalog"] else "",
        ", convention plugins in `%s/`" % info["build_logic"] if info["build_logic"] else ""))
    if f.get("ksp") or f.get("kapt"):
        stack.append("- Code generation: %s" % " and ".join(n for n, k in (("KSP", "ksp"), ("kapt", "kapt")) if f.get(k)))
    if info["tests"]:
        stack.append("- Tests: %s" % ", ".join(info["tests"]))
    if info["lint_tools"]:
        stack.append("- Static analysis: Android Lint, %s" % ", ".join(info["lint_tools"]))

    # Commands
    example = _example_module(info)
    cmd_lines = [
        "| Purpose | Command |",
        "| --- | --- |",
        "| Build (debug) | `%s` |" % cmds["build"],
        "| Unit tests | `%s` |" % cmds["test"],
        "| One module's tests | `%s %s:%s` |" % (g, example, module_test_task(_module(info, example))),
        "| Lint | `%s` |" % cmds["lint"],
    ]
    if "format" in cmds:
        cmd_lines.append("| Format | `%s` |" % cmds["format"])
    if "instrumented" in cmds:
        cmd_lines.append("| Instrumented tests (needs a device; only when asked) | `%s` |" % cmds["instrumented"])
    cmd_lines.append("| Dependencies of a module | `%s %s:dependencies --configuration %sRuntimeClasspath` |" % (
        g, info["app_module"] or example, info.get("variant") or "debug"))

    # Build variants
    variants = []
    for m in info["modules"]:
        if m.get("flavors"):
            dims = m.get("flavor_dimensions") or []
            variants.append("- `%s` has product flavors %s%s. Commands use the `%s` variant. Build other flavors or release variants only when asked." % (
                m["path"], ", ".join("`%s`" % x for x in m["flavors"]),
                " (dimension%s %s)" % ("s" if len(dims) > 1 else "", ", ".join("`%s`" % d for d in dims)) if dims else "",
                m["variant"]))
    if info.get("flavors_in_build_logic"):
        variants.append("- Product flavors are configured in the convention plugins (`%s/`). TODO: check the variant name and update the commands above (for example `assembleDemoDebug`)." % info["build_logic"])
    variants_note = ("### Build variants\n\n" + "\n".join(variants)) if variants else ""

    # Architecture
    arch = [
        "- Layers: UI → ViewModel (state holder) → use cases (optional) → repositories → data sources. Dependencies point inward, and UI never talks to data sources directly.",
        "- Unidirectional data flow: a ViewModel exposes one immutable `StateFlow<UiState>` and receives user actions as function calls or events. Match the style (MVVM or MVI) already used in the module you touch, and do not introduce a new one.",
        "- ViewModels never hold `Context`, Views, composables or Activity references.",
    ]
    if di == "Hilt":
        arch.append("- DI with Hilt: `@HiltViewModel` + `@Inject constructor(...)`. Bind interfaces in `@Module @InstallIn(...)` classes next to the existing ones. No manual singletons or service locators.")
    elif di == "Koin":
        arch.append("- DI with Koin: declare new types in the existing Koin modules and use `koinViewModel()`/`viewModelOf`. No manual singletons.")
    else:
        arch.append("- Use constructor injection and follow the existing wiring. Do not add a DI framework unless asked.")
    if f.get("coroutines"):
        arch.append("- Coroutines: launch in `viewModelScope` (or the owning scope), inject dispatchers instead of hardcoding `Dispatchers.IO`, expose `Flow` for streams and `suspend` for one-shot calls. Never use `GlobalScope`, and never use `runBlocking` in production code.")
    if f.get("room"):
        arch.append("- Room: DAOs return `Flow` for observed queries and `suspend` for writes. Any schema change needs a version bump and a `Migration` with a migration test. Never enable destructive migration without asking.")
    if f.get("sqldelight"):
        arch.append("- SQLDelight: change schema through `.sq`/`.sqm` files with a migration. Never hand-edit generated code.")
    arch.append("- Errors: map exceptions to domain results at the repository boundary, and show errors through `UiState`. Do not swallow exceptions or catch `CancellationException`.")

    # Preset section
    preset_text = _template("agents", "presets", "%s.md" % preset).strip()
    kmp_ui = ""
    if preset == "kmp":
        if f.get("compose_multiplatform"):
            kmp_ui = "- **Compose Multiplatform.** Shared UI goes in `commonMain` using `org.jetbrains.compose` APIs and `Res` resources. Android-only UI APIs stay in `androidMain`. Hoist state and add previews as for Jetpack Compose."
        elif f.get("compose"):
            kmp_ui = "- **UI.** Android UI is Jetpack Compose in the Android app module. Follow Compose conventions: state hoisting, `collectAsStateWithLifecycle()`, `@Preview` for every new screen, theme tokens only."
        else:
            kmp_ui = "- **UI.** UI is platform-native. Keep UI out of shared modules and expose state as `StateFlow` from shared state holders."
    preset_text = preset_text.replace("{{KMP_UI_NOTE}}", kmp_ui).rstrip()

    # Catalog
    if info["version_catalog"]:
        catalog = "\n".join([
            "- Declare every dependency and plugin in `gradle/libs.versions.toml` (`[versions]`, `[libraries]`, `[plugins]`) and reference it as `libs.…` / `alias(libs.plugins.…)`. Never hardcode coordinates or versions in a build file.",
            "- Before adding a library, check whether the catalog or the platform already covers the need. List every new dependency in your summary with the reason.",
            "- Do not upgrade existing versions unless the task asks for it.",
        ])
    else:
        catalog = "\n".join([
            "- This project does not use a version catalog. Declare dependencies the way existing build files do, and do not introduce a catalog unless asked.",
            "- Before adding a library, check whether an existing dependency or the platform already covers the need. List every new dependency in your summary.",
            "- Do not upgrade existing versions unless the task asks for it.",
        ])

    # Testing
    t = info["tests"]
    testing = [
        "- Every new ViewModel, use case and repository function gets unit tests in the module's `src/test` (or `commonTest` for shared KMP code). Every bug fix gets a regression test.",
        "- Use `runTest` from coroutines-test%s and replace `Dispatchers.Main` with a test dispatcher rule." % (" (already in the project)" if "coroutines-test" in t else ""),
    ]
    if "Turbine" in t:
        testing.append("- Test flows with Turbine (`test { awaitItem() }`).")
    if "MockK" in t or "Mockito" in t:
        testing.append("- Prefer hand-written fakes for the project's own interfaces. Use %s only for third-party types." % ("MockK" if "MockK" in t else "Mockito"))
    else:
        testing.append("- Prefer hand-written fakes over mocks.")
    if "Compose UI test" in t or f.get("compose"):
        testing.append("- Compose UI tests target the stateless content composable with `createComposeRule()`%s." % (" (Robolectric is available for JVM UI tests)" if "Robolectric" in t else ""))
    if "Roborazzi/Paparazzi" in t:
        testing.append("- Screenshot tests exist. Re-record them only when a UI change is intended, and say so.")
    testing.append("- Never delete, `@Ignore` or weaken a failing test to get a green build. Fix the code, or explain why the test is wrong.")
    if not t:
        testing.append("- TODO: no test libraries were detected. Add the project's testing conventions here.")

    # Never touch extras
    extra = []
    if f.get("room"):
        extra.append("- Exported Room schemas (`schemas/**.json`): generated by the build. Commit them, never hand-edit them.")
    if f.get("kmp"):
        extra.append("- Xcode project settings and `iosApp/` signing configuration")
    extra_text = ("\n".join(extra) + "\n") if extra else ""

    # Done checklist
    done = [
        "- [ ] `%s` succeeds" % cmds["build"],
        "- [ ] Unit tests pass for every module you touched (`%s`, or the module-scoped task)" % cmds["test"],
        "- [ ] `%s` reports no new issues" % cmds["lint"],
    ]
    if preset in ("compose", "views-compose") or f.get("compose"):
        done.append("- [ ] Every new or changed composable screen and component has a `@Preview`")
    done += [
        "- [ ] New logic has tests, and no existing test was deleted, ignored or weakened",
        "- [ ] Dependencies go through %s, and nothing in the Never touch list changed" % ("the version catalog" if info["version_catalog"] else "the existing build files"),
        "- [ ] Your summary lists the commands you ran with their results, and anything you could not verify (for example instrumented tests that need a device)",
    ]

    # Skills index
    skills_index = []
    for name in SKILLS:
        fm, _ = split_frontmatter(_template("skills", "%s.md" % name))
        skills_index.append("- `%s` (`.agents/skills/%s/SKILL.md`): %s" % (name, name, frontmatter_value(fm, "description")))

    bl = info["build_logic"]
    return {
        "PROJECT_NAME": info["project_name"],
        "VERSION": __version__,
        "PRESET": preset,
        "PROJECT_MAP": project_map,
        "STACK": "\n".join(stack),
        "COMMANDS": "\n".join(cmd_lines),
        "VARIANTS_NOTE": variants_note,
        "ARCHITECTURE": "\n".join(arch),
        "PRESET_SECTION": preset_text,
        "SETTINGS_FILE": info["settings_file"],
        "BUILD_LOGIC_NOTE": (", applying the convention plugins from `%s/` instead of configuring Android and Kotlin by hand" % bl) if bl else "",
        "CATALOG_RULES": catalog,
        "TESTING": "\n".join(testing),
        "EXTRA_NEVER_TOUCH": extra_text,
        "DONE": "\n".join(done),
        "SKILLS_INDEX": "\n".join(skills_index),
        "_BUILD": cmds["build"],
        "_TEST": cmds["test"],
        "_LINT": cmds["lint"],
    }


def fill(template, ctx):
    # type: (str, Dict[str, str]) -> str
    def repl(m):
        key = m.group(1)
        if key not in ctx:
            raise KeyError("Unknown template placeholder: %s" % key)
        return ctx[key]
    text = re.sub(r"\{\{([A-Z_]+)\}\}", repl, template)
    return re.sub(r"\n{3,}", "\n\n", text)


# --------------------------------------------------------------------------- #
# Planning: which files get which blocks
# --------------------------------------------------------------------------- #

class Target(object):
    """A file the playbook manages, as a marker block plus an optional prefix for new files."""

    def __init__(self, path, body, prefix="", shared=False):
        # type: (str, str, str, bool) -> None
        self.path = path          # relative, forward slashes
        self.body = body
        self.prefix = prefix      # written only when the file is created (e.g. frontmatter)
        self.shared = shared      # shared files get the block appended if they lack markers


def build_targets(info, preset, agents):
    # type: (Dict, str, List[str]) -> List[Target]
    ctx = render_context(info, preset)
    targets = [Target("AGENTS.md", fill(_template("agents", "base.md"), ctx), shared=True)]

    for name in SKILLS:
        fm, body = split_frontmatter(_template("skills", "%s.md" % name))
        targets.append(Target(".agents/skills/%s/SKILL.md" % name, body, prefix=fm))

    commands_list = ", ".join("`/%s`" % s for s in SKILLS)
    if "claude" in agents:
        targets.append(Target("CLAUDE.md", "\n".join([
            "@AGENTS.md",
            "",
            "The project rules for this repository are in `AGENTS.md` (imported above). Follow them, including the Never touch list and the Done checklist.",
            "",
            "Slash commands: %s. Each one follows the matching playbook in `.agents/skills/`." % commands_list,
        ]), shared=True))
        for name in SKILLS:
            fm, _ = split_frontmatter(_template("skills", "%s.md" % name))
            prefix = "---\ndescription: %s\nargument-hint: %s\n---\n" % (
                frontmatter_value(fm, "description"), ARG_HINTS[name])
            targets.append(Target(".claude/commands/%s.md" % name, "\n".join([
                "Read `AGENTS.md`, then follow the playbook in `.agents/skills/%s/SKILL.md` step by step." % name,
                "",
                "Task: $ARGUMENTS",
            ]), prefix=prefix))

    if "cursor" in agents:
        targets.append(Target(".cursor/rules/android-agent-playbook.mdc", "\n".join([
            "Follow the repository rules in `AGENTS.md` at the project root: commands, architecture, module rules, the Never touch list and the Done checklist.",
            "",
            "Before finishing any change, run:",
            "",
            "- `%s`" % ctx["_BUILD"],
            "- `%s`" % ctx["_TEST"],
            "- `%s`" % ctx["_LINT"],
            "",
            "Playbooks for common tasks live in `.agents/skills/`. The matching commands are %s." % commands_list,
        ]), prefix="---\ndescription: Android project rules from android-agent-playbook\nalwaysApply: true\n---\n"))
        for name in SKILLS:
            title = name.replace("-", " ").capitalize()
            targets.append(Target(".cursor/commands/%s.md" % name, "\n".join([
                "# %s" % title,
                "",
                "Read `AGENTS.md`, then follow the playbook in `.agents/skills/%s/SKILL.md` step by step for the request that follows this command." % name,
            ])))

    if "copilot" in agents:
        targets.append(Target(".github/copilot-instructions.md", "\n".join([
            "This is an Android project. The full rules for AI assistants are in [`AGENTS.md`](../AGENTS.md) at the repository root. Read and follow it.",
            "",
            "Key points:",
            "",
            "- Build: `%s`. Unit tests: `%s`. Lint: `%s`." % (ctx["_BUILD"], ctx["_TEST"], ctx["_LINT"]),
            "- Follow the existing architecture and module boundaries. Feature modules never depend on each other.",
            "- %s" % ("Add dependencies only through `gradle/libs.versions.toml`." if info["version_catalog"] else "Declare dependencies the way existing build files do."),
            "- Never edit `build/`, generated code, `local.properties`, signing config, keystores or `google-services.json`.",
            "- New logic needs unit tests%s." % (", and new composables need a `@Preview`" if (preset != "kmp" or info["features"].get("compose")) else ""),
            "- Playbooks for common tasks (adding a screen or module, migrating to Compose, writing tests, fixing the build) are in `.agents/skills/`.",
        ]), shared=True))

    return targets


# --------------------------------------------------------------------------- #
# Marker-block editing
# --------------------------------------------------------------------------- #

def make_block(body):
    # type: (str) -> str
    return "%s\n%s\n%s\n" % (START, body.strip("\n"), END)


def apply_block(existing, target):
    # type: (Optional[str], Target) -> Tuple[str, Optional[str]]
    """Return (action, new_text). Actions: create, update, unchanged, append, skip, error."""
    block = make_block(target.body)
    if existing is None:
        return "create", target.prefix + block
    starts, ends = existing.count(START), existing.count(END)
    if starts == 1 and ends == 1 and existing.index(START) < existing.index(END):
        s = existing.index(START)
        e = existing.index(END) + len(END)
        if e < len(existing) and existing[e] == "\n":
            e += 1
        new = existing[:s] + block + existing[e:]
        return ("unchanged" if new == existing else "update"), new
    if starts or ends:
        return "error", None
    if target.shared:
        if not existing.strip():
            return "append", block
        return "append", existing.rstrip("\n") + "\n\n" + block
    return "skip", None


def remove_block(existing):
    # type: (str) -> Tuple[str, Optional[str]]
    """Return (action, new_text). new_text None with action 'delete' means remove the file."""
    if existing.count(START) != 1 or existing.count(END) != 1:
        return ("error" if (START in existing or END in existing) else "absent"), None
    s = existing.index(START)
    e = existing.index(END) + len(END)
    if e < len(existing) and existing[e] == "\n":
        e += 1
    parts = [p for p in (existing[:s].rstrip("\n"), existing[e:].strip("\n")) if p.strip()]
    rest = "\n\n".join(parts) + "\n" if parts else ""
    fm, body = split_frontmatter(rest)
    if not body.strip():
        return "delete", None
    return "update", rest


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

def _abs(root, rel):
    # type: (str, str) -> str
    return os.path.join(root, *rel.split("/"))


def _write(path, text):
    # type: (str, str) -> None
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _diff(rel, old, new):
    # type: (str, Optional[str], Optional[str]) -> str
    a = (old or "").splitlines(True)
    b = (new or "").splitlines(True)
    return "".join(difflib.unified_diff(a, b, "a/" + rel if old is not None else "/dev/null",
                                        "b/" + rel if new is not None else "/dev/null"))


def summarize(info):
    # type: (Dict) -> str
    f = info["features"]
    bits = ["Kotlin DSL" if info["dsl"] == "kts" else "Groovy DSL" if info["dsl"] else "no Gradle settings"]
    bits.append("%d module%s" % (len(info["modules"]), "" if len(info["modules"]) == 1 else "s"))
    for label, key in (("KMP", "kmp"), ("Compose", "compose"), ("Views", "views"), ("Hilt", "hilt"),
                       ("Koin", "koin"), ("Room", "room"), ("SQLDelight", "sqldelight")):
        if f.get(key):
            bits.append(label)
    if info.get("variant", "debug") != "debug":
        bits.append("variant %s" % info["variant"])
    if (info.get("build") or {}).get("min_sdk"):
        bits.append("minSdk %s" % info["build"]["min_sdk"])
    if info["version_catalog"]:
        bits.append("version catalog")
    if info["build_logic"]:
        bits.append("convention plugins")
    return " · ".join(bits)


def _parse_agents(value):
    # type: (str) -> List[str]
    agents = [a.strip().lower() for a in value.split(",") if a.strip()]
    if agents == ["all"]:
        return list(AGENTS)
    bad = [a for a in agents if a not in AGENTS]
    if bad:
        raise argparse.ArgumentTypeError("unknown agent(s): %s (choose from %s)" % (", ".join(bad), ", ".join(AGENTS)))
    return agents


def cmd_detect(args):
    # type: (argparse.Namespace) -> int
    info = detect(args.path)
    if args.json:
        print(json.dumps(info, indent=2, sort_keys=True))
        return 0
    print("%s  (%s)" % (info["project_name"], info["root"]))
    print("  %s" % summarize(info))
    for m in info["modules"]:
        print("  %-28s %s" % (m["path"], m["type"]))
    print("  tests: %s" % (", ".join(info["tests"]) or "none detected"))
    print("  suggested preset: %s" % info["preset"])
    return 0


def cmd_install(args):
    # type: (argparse.Namespace) -> int
    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print("error: %s is not a directory" % root, file=sys.stderr)
        return 2
    info = detect(root)
    if not info["is_gradle"] and not args.force:
        print("error: no settings.gradle(.kts) or build.gradle(.kts) in %s. Run this from an Android project root, or pass --force." % root, file=sys.stderr)
        return 2
    preset = info["preset"] if args.preset == "auto" else args.preset
    agents = args.agents
    print("%s %s → %s" % (MARK, __version__, root))
    print("Detected: %s" % summarize(info))
    print("Preset: %s%s · Agents: %s" % (preset, " (auto)" if args.preset == "auto" else "", ", ".join(agents)))
    print("")

    counts = {}  # type: Dict[str, int]
    problems = 0
    for t in build_targets(info, preset, agents):
        path = _abs(root, t.path)
        existing = _read(path) if os.path.isfile(path) else None
        action, new = apply_block(existing, t)
        counts[action] = counts.get(action, 0) + 1
        note = ""
        if action == "skip":
            note = "  (exists without %s markers; left untouched)" % MARK
        elif action == "error":
            note = "  (unbalanced %s markers; fix by hand)" % MARK
            problems += 1
        print("  %-9s %s%s" % (action, t.path, note))
        if args.diff and new is not None and action in ("create", "update", "append"):
            print(_diff(t.path, existing, new))
        if not args.dry_run and new is not None and action in ("create", "update", "append"):
            _write(path, new)

    print("")
    summary = ", ".join("%d %s" % (n, a) for a, n in sorted(counts.items()))
    if args.dry_run:
        print("Dry run: nothing written (%s)." % summary)
    else:
        print("Done: %s." % summary)
        print("Next: review AGENTS.md (fill in the TODO lines), commit the files, then try `/add-screen` in Claude Code or Cursor.")
    return 1 if problems else 0


def cmd_uninstall(args):
    # type: (argparse.Namespace) -> int
    root = os.path.abspath(args.path)
    paths = ["AGENTS.md", "CLAUDE.md", ".cursor/rules/android-agent-playbook.mdc", ".github/copilot-instructions.md"]
    for name in SKILLS:
        paths += [".agents/skills/%s/SKILL.md" % name, ".claude/commands/%s.md" % name, ".cursor/commands/%s.md" % name]
    problems = 0
    for rel in paths:
        path = _abs(root, rel)
        if not os.path.isfile(path):
            continue
        old = _read(path)
        action, new = remove_block(old)
        if action == "absent":
            continue
        if action == "error":
            problems += 1
        print("  %-9s %s" % (action, rel))
        if args.diff and action in ("update", "delete"):
            print(_diff(rel, old, new))
        if args.dry_run:
            continue
        if action == "update" and new is not None:
            _write(path, new)
        elif action == "delete":
            os.remove(path)
            d = os.path.dirname(path)
            while d != root and os.path.isdir(d) and not os.listdir(d):
                os.rmdir(d)
                d = os.path.dirname(d)
    if args.dry_run:
        print("Dry run: nothing changed.")
    return 1 if problems else 0


def build_parser():
    # type: () -> argparse.ArgumentParser
    p = argparse.ArgumentParser(
        prog=MARK,
        description="AI agent rules and commands for Android projects (Claude Code, Codex, Cursor, Copilot).")
    p.add_argument("--version", action="version", version="%(prog)s " + __version__)
    sub = p.add_subparsers(dest="command")

    d = sub.add_parser("detect", help="show what was detected in an Android project")
    d.add_argument("path", nargs="?", default=".")
    d.add_argument("--json", action="store_true", help="print machine-readable JSON")
    d.set_defaults(func=cmd_detect)

    i = sub.add_parser("install", help="write or refresh the agent files (safe to re-run)")
    i.add_argument("path", nargs="?", default=".")
    i.add_argument("--preset", choices=("auto",) + PRESETS, default="auto")
    i.add_argument("--agents", type=_parse_agents, default=list(AGENTS),
                   help="comma-separated: claude,codex,cursor,copilot (default: all)")
    i.add_argument("--dry-run", action="store_true", help="show what would change without writing")
    i.add_argument("--diff", action="store_true", help="print a unified diff of each change")
    i.add_argument("--force", action="store_true", help="install even if no Gradle files are found")
    i.set_defaults(func=cmd_install)

    u = sub.add_parser("uninstall", help="remove the playbook blocks, keeping your own text")
    u.add_argument("path", nargs="?", default=".")
    u.add_argument("--dry-run", action="store_true")
    u.add_argument("--diff", action="store_true")
    u.set_defaults(func=cmd_uninstall)
    return p


def main(argv=None):
    # type: (Optional[List[str]]) -> int
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
