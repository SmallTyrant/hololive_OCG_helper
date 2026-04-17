#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("detect_scope.py")
SPEC = importlib.util.spec_from_file_location("detect_scope", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

detect_scope = MODULE.detect_scope
classify_file = MODULE.classify_file


class DetectScopeTest(unittest.TestCase):
    def test_db_file_is_db_not_tools(self) -> None:
        self.assertEqual(classify_file("app/assets/hololive_ocg.sqlite"), "db")

    def test_android_scope_includes_native_app(self) -> None:
        result = detect_scope(
            [
                "mobile/android/native/src/main/java/com/example/Foo.kt",
                "mobile/android/native-app/app/src/main/AndroidManifest.xml",
            ]
        )
        self.assertEqual(result.scope, "android")

    def test_ios_scope_includes_native_app(self) -> None:
        result = detect_scope(
            [
                "mobile/ios/native/Sources/HocgNative/HocgViewModel.swift",
                "mobile/ios/native-app/project.yml",
            ]
        )
        self.assertEqual(result.scope, "ios")

    def test_builder_scope_matches_workflows_and_actions(self) -> None:
        workflow_result = detect_scope([".github/workflows/swarm-min.yml"])
        action_result = detect_scope([".github/actions/opencode-run/action.yml"])
        self.assertEqual(workflow_result.scope, "builder")
        self.assertEqual(action_result.scope, "builder")

    def test_tools_scope_matches_scripts_and_app_python(self) -> None:
        scripts_result = detect_scope(["scripts/run_quality_loop.py"])
        app_result = detect_scope(["app/ui.py"])
        self.assertEqual(scripts_result.scope, "tools")
        self.assertEqual(app_result.scope, "tools")

    def test_mixed_scope_detected(self) -> None:
        result = detect_scope(
            [
                "mobile/android/native/src/main/java/com/example/Foo.kt",
                "app/assets/hololive_ocg.sqlite",
            ]
        )
        self.assertEqual(result.scope, "mixed")
        self.assertEqual(result.scopes, ("android", "db"))

    def test_none_scope_for_docs_only(self) -> None:
        result = detect_scope(["README.md", ".gitignore", ".github/release-notes/android/1.2.18.md"])
        self.assertEqual(result.scope, "none")


if __name__ == "__main__":
    unittest.main()
