#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("discord_cmux_bot.py")
SPEC = importlib.util.spec_from_file_location("discord_cmux_bot", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

parse_id_set = MODULE.parse_id_set
extract_openai_text = MODULE.extract_openai_text
format_command_output = MODULE.format_command_output
truncate_discord_text = MODULE.truncate_discord_text


class DiscordCmuxBotTest(unittest.TestCase):
    def test_parse_id_set_accepts_csv_and_whitespace(self) -> None:
        self.assertEqual(parse_id_set("123, 456\n789"), frozenset({123, 456, 789}))

    def test_extract_openai_text_uses_nested_message_output(self) -> None:
        payload = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "안녕하세요."},
                        {"type": "output_text", "text": " 반갑습니다."},
                    ],
                }
            ]
        }
        self.assertEqual(extract_openai_text(payload), "안녕하세요. 반갑습니다.")

    def test_format_command_output_includes_exit_code(self) -> None:
        text = format_command_output(0, "hello", "warning")
        self.assertIn("[stdout]", text)
        self.assertIn("[stderr]", text)
        self.assertIn("[exit code] 0", text)

    def test_truncate_discord_text_limits_length(self) -> None:
        result = truncate_discord_text("a" * 2000, limit=50)
        self.assertEqual(len(result), 50)
        self.assertTrue(result.endswith("…"))


if __name__ == "__main__":
    unittest.main()
