#!/usr/bin/env python3

from __future__ import annotations

import asyncio
import io
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import discord
import requests
from discord import app_commands
from discord.ext import commands


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
DEFAULT_RESPONSE_LIMIT = 1900
ALLOWED_ROLES = (
    "coordinator",
    "planner",
    "python-app",
    "android-native",
    "ios-native",
    "ci-workflows",
    "reviewer",
)


SYSTEM_PROMPT = """\
You are the Discord assistant for the hololive_OCG_helper cmux workspace.

Rules:
- Reply in Korean unless the user clearly asks for another language.
- Be concise, actionable, and explicit about what you checked.
- If the user asks about the repo or workspace, prefer concrete status and commands over speculation.
- Do not invent cmux output. If the bot provided workspace/status output, cite that output.
- If the answer depends on unavailable context, say what is missing and what to run next.
"""


@dataclass(frozen=True)
class BotConfig:
    discord_token: str
    openai_api_key: str
    openai_model: str
    allowed_user_ids: frozenset[int]
    allowed_channel_ids: frozenset[int]
    guild_id: int | None
    ephemeral_responses: bool


def parse_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def parse_id_set(raw: str | None) -> frozenset[int]:
    if raw is None or not raw.strip():
        return frozenset()
    values: set[int] = set()
    for chunk in re.split(r"[,\s]+", raw.strip()):
        if not chunk:
            continue
        try:
            values.add(int(chunk))
        except ValueError as exc:
            raise ValueError(f"Invalid Discord user ID: {chunk}") from exc
    return frozenset(values)


def parse_optional_int(raw: str | None) -> int | None:
    if raw is None or not raw.strip():
        return None
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"Invalid integer value: {raw}") from exc


def load_config() -> BotConfig:
    discord_token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
    allowed_user_ids = parse_id_set(os.getenv("DISCORD_ALLOWED_USER_IDS"))
    allowed_channel_ids = parse_id_set(os.getenv("DISCORD_ALLOWED_CHANNEL_IDS"))
    guild_id = parse_optional_int(os.getenv("DISCORD_GUILD_ID"))
    ephemeral_responses = parse_bool(os.getenv("DISCORD_EPHEMERAL_RESPONSES"), default=True)

    if not discord_token:
        raise SystemExit("DISCORD_BOT_TOKEN is required.")

    return BotConfig(
        discord_token=discord_token,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        allowed_user_ids=allowed_user_ids,
        allowed_channel_ids=allowed_channel_ids,
        guild_id=guild_id,
        ephemeral_responses=ephemeral_responses,
    )


def truncate_discord_text(text: str, limit: int = DEFAULT_RESPONSE_LIMIT) -> str:
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 1] + "…"


def render_code_block(text: str) -> str:
    body = text.strip() or "(no output)"
    return f"```text\n{body}\n```"


def extract_openai_text(payload: dict) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    parts: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text", "")
                if isinstance(text, str):
                    parts.append(text)

    return "".join(parts).strip()


async def run_command(command: list[str], cwd: Path, timeout: int = 600) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return 124, "", f"Command timed out after {timeout} seconds: {' '.join(command)}"
    return (
        proc.returncode,
        stdout_bytes.decode("utf-8", errors="replace"),
        stderr_bytes.decode("utf-8", errors="replace"),
    )


def format_command_output(returncode: int, stdout: str, stderr: str) -> str:
    sections: list[str] = []
    if stdout.strip():
        sections.append("[stdout]\n" + stdout.strip())
    if stderr.strip():
        sections.append("[stderr]\n" + stderr.strip())
    if not sections:
        sections.append("(no output)")
    sections.append(f"[exit code] {returncode}")
    return "\n\n".join(sections)


async def send_text_or_file(interaction: discord.Interaction, text: str, filename: str) -> None:
    cleaned = text.strip() or "(no output)"
    if len(cleaned) <= 1900:
        await interaction.followup.send(render_code_block(cleaned))
        return

    payload = io.BytesIO(cleaned.encode("utf-8"))
    await interaction.followup.send(
        "결과가 길어서 파일로 보냅니다.",
        file=discord.File(payload, filename=filename),
    )


async def ask_openai(config: BotConfig, prompt: str) -> str:
    if not config.openai_api_key:
        return "OPENAI_API_KEY가 설정되어 있지 않습니다."

    def _request() -> dict:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {config.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.openai_model,
                "instructions": SYSTEM_PROMPT,
                "input": prompt,
                "max_output_tokens": 700,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()

    payload = await asyncio.to_thread(_request)
    text = extract_openai_text(payload)
    if text:
        return text

    return json.dumps(payload, ensure_ascii=False, indent=2)


def is_authorized(config: BotConfig, interaction: discord.Interaction) -> bool:
    if not config.allowed_user_ids:
        return True
    user = interaction.user
    user_id = getattr(user, "id", None)
    return isinstance(user_id, int) and user_id in config.allowed_user_ids


def is_allowed_channel(config: BotConfig, interaction: discord.Interaction) -> bool:
    if not config.allowed_channel_ids:
        return True
    channel_id = interaction.channel_id
    return isinstance(channel_id, int) and channel_id in config.allowed_channel_ids


def build_bot(config: BotConfig) -> commands.Bot:
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)
    sync_guild = discord.Object(id=config.guild_id) if config.guild_id else None
    cmux_script = ROOT / "scripts" / "opencode_parallel" / "start_role.sh"

    @bot.event
    async def setup_hook() -> None:
        if sync_guild is not None:
            bot.tree.copy_global_to(guild=sync_guild)
            synced = await bot.tree.sync(guild=sync_guild)
            print(f"Synced {len(synced)} guild command(s) to {config.guild_id}")
        else:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} global command(s)")

    async def respond_unauthorized(interaction: discord.Interaction) -> None:
        if interaction.response.is_done():
            await interaction.followup.send("이 봇은 허용된 사용자만 사용할 수 있습니다.", ephemeral=True)
        else:
            await interaction.response.send_message("이 봇은 허용된 사용자만 사용할 수 있습니다.", ephemeral=True)

    async def respond_wrong_channel(interaction: discord.Interaction) -> None:
        message = "이 봇은 지정된 채널에서만 사용할 수 있습니다."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    async def ensure_authorized(interaction: discord.Interaction) -> bool:
        if is_authorized(config, interaction):
            return True
        await respond_unauthorized(interaction)
        return False

    async def ensure_allowed_context(interaction: discord.Interaction) -> bool:
        if not await ensure_authorized(interaction):
            return False
        if is_allowed_channel(config, interaction):
            return True
        await respond_wrong_channel(interaction)
        return False

    cmux_group = app_commands.Group(name="cmux", description="cmux workspace commands")

    @bot.tree.command(name="ask", description="Ask OpenAI and get a reply in Discord")
    @app_commands.describe(prompt="질문 또는 명령")
    async def ask(interaction: discord.Interaction, prompt: str) -> None:
        if not await ensure_allowed_context(interaction):
            return
        await interaction.response.defer(ephemeral=config.ephemeral_responses)
        try:
            answer = await ask_openai(config, prompt)
        except Exception as exc:  # noqa: BLE001 - surface the actual API error to the operator
            answer = f"OpenAI 호출 실패: {exc}"
        await send_text_or_file(interaction, answer, "openai-answer.txt")

    @cmux_group.command(name="status", description="List cmux workspaces")
    async def status(interaction: discord.Interaction) -> None:
        if not await ensure_allowed_context(interaction):
            return
        await interaction.response.defer(ephemeral=config.ephemeral_responses)
        code, stdout, stderr = await run_command(["cmux", "list-workspaces"], cwd=ROOT, timeout=60)
        await send_text_or_file(
            interaction,
            format_command_output(code, stdout, stderr),
            "cmux-status.txt",
        )

    @cmux_group.command(name="start", description="Start a cmux workspace for a role")
    @app_commands.describe(role="워크스페이스 역할")
    @app_commands.choices(role=[app_commands.Choice(name=role, value=role) for role in ALLOWED_ROLES])
    async def start(interaction: discord.Interaction, role: app_commands.Choice[str]) -> None:
        if not await ensure_allowed_context(interaction):
            return
        await interaction.response.defer(ephemeral=config.ephemeral_responses)
        code, stdout, stderr = await run_command(["bash", str(cmux_script), role.value], cwd=ROOT, timeout=120)
        await send_text_or_file(
            interaction,
            format_command_output(code, stdout, stderr),
            f"cmux-start-{role.value}.txt",
        )

    @cmux_group.command(name="capture", description="Capture pane output from a cmux workspace")
    @app_commands.describe(
        workspace_ref="cmux workspace ref",
        surface_ref="surface ref",
        lines="scrollback line count",
    )
    async def capture(
        interaction: discord.Interaction,
        workspace_ref: str,
        surface_ref: str,
        lines: app_commands.Range[int, 1, 200] = 80,
    ) -> None:
        if not await ensure_allowed_context(interaction):
            return
        await interaction.response.defer(ephemeral=config.ephemeral_responses)
        code, stdout, stderr = await run_command(
            [
                "cmux",
                "capture-pane",
                "--workspace",
                workspace_ref,
                "--surface",
                surface_ref,
                "--scrollback",
                "--lines",
                str(lines),
            ],
            cwd=ROOT,
            timeout=60,
        )
        await send_text_or_file(
            interaction,
            format_command_output(code, stdout, stderr),
            f"cmux-capture-{workspace_ref}-{surface_ref}.txt",
        )

    bot.tree.add_command(cmux_group)
    return bot


async def main() -> None:
    config = load_config()
    bot = build_bot(config)
    await bot.start(config.discord_token)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
