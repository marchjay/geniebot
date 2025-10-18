from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

import discord
from discord import app_commands
from storage import (
    get_genie_channel_id,
    set_genie_channel_id,
)

logger = logging.getLogger(__name__)


class DiscordBot(discord.Client):
    def __init__(
        self,
        *,
        allowed_channel_ids: List[int],
        system_prompt: str,
        llm_client,
        thread_name_template: str = "genie-{author}-{id}",
    ) -> None:
        intents = discord.Intents.default()
        intents.message_content = True  # Requires enabling in Discord Developer Portal
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

        # Load persisted genie channel if available; otherwise use env-provided list
        persisted_genie = get_genie_channel_id()
        if persisted_genie:
            self.allowed_channel_ids = {persisted_genie}
        else:
            self.allowed_channel_ids = set(allowed_channel_ids or [])
        self.system_prompt = system_prompt
        self.llm = llm_client
        self.thread_name_template = thread_name_template

    def _format_thread_name(self, message: discord.Message) -> str:
        # Build from template; allow placeholders: {author}, {id}, {channel}, {user_id}
        safe_author = (message.author.name or "agent").strip()
        # Sanitize author to avoid slashes/newlines and trim spaces
        safe_author = " ".join(safe_author.split())
        base = self.thread_name_template.format(
            author=safe_author,
            id=message.id,
            channel=getattr(message.channel, "name", getattr(message.channel, "id", "channel")),
            user_id=getattr(message.author, "id", "user"),
        )
        # Discord thread name max length ~100
        name = base[:100]
        # Remove problematic characters
        forbidden = "\n\r\t"  # keep it simple
        for ch in forbidden:
            name = name.replace(ch, " ")
        name = name.strip() or f"genie-{message.id}"
        return name

    async def on_ready(self):
        logger.info("Logged in as %s (ID: %s)", self.user, getattr(self.user, "id", "?"))
        # Sync slash commands (global and per guild for immediate availability)
        try:
            await self.tree.sync()
        except Exception:
            pass
        for g in list(getattr(self, "guilds", [])):
            try:
                await self.tree.sync(guild=g)
            except Exception:
                continue
        # No legacy guidelines-channel loading

    async def setup_hook(self) -> None:  # type: ignore[override]
        # Define slash commands

        @app_commands.command(name="genie_channel", description="Set the channel where Genie will respond and listen")
        @app_commands.describe(channel="The channel to use for Genie replies")
        async def genie_channel_cmd(interaction: discord.Interaction, channel: discord.TextChannel):
            # Admin check
            member = interaction.user if isinstance(interaction.user, discord.Member) else None
            if not member or not member.guild_permissions.administrator:
                await interaction.response.send_message("Admin only.", ephemeral=True)
                return
            self.allowed_channel_ids = {channel.id}
            set_genie_channel_id(channel.id)
            await interaction.response.send_message(
                f"Genie channel set to #{channel.name}.", ephemeral=True
            )

        # Register commands
        self.tree.add_command(genie_channel_cmd)
        # Removed legacy guidelines commands

    async def on_message(self, message: discord.Message):
        # Ignore ourselves and other bots
        if message.author.bot:
            return

        content = message.content.strip()
        if not content:
            return

        # Legacy '!' admin commands removed in favor of slash commands

        # After admin commands, enforce allowed channels if configured
        if self.allowed_channel_ids:
            try:
                parent_id = None
                if isinstance(message.channel, discord.Thread):
                    parent_id = getattr(message.channel, "parent_id", None)
                allowed = (
                    (message.channel.id in self.allowed_channel_ids)
                    or (parent_id in self.allowed_channel_ids)
                )
                if not allowed:
                    return
            except Exception:
                return

        # Decide target: create a thread for this message if we're in a text channel;
        # if already in a thread, continue within it. Fallback to channel on errors.
        target_channel: discord.abc.MessageableChannel = message.channel
        created_thread: Optional[discord.Thread] = None
        if isinstance(message.channel, discord.TextChannel):
            thread_name = self._format_thread_name(message)
            try:
                # Create a PRIVATE thread linked to the triggering message
                created_thread = await message.channel.create_thread(
                    name=thread_name,
                    type=discord.ChannelType.private_thread,
                    auto_archive_duration=1440,
                    invitable=False,
                    message=message,
                )
                # Ensure the author is a member of the private thread
                try:
                    await created_thread.add_user(message.author)
                except Exception:
                    pass
                target_channel = created_thread
                logger.info(
                    "Created PRIVATE thread %s (%s) for message %s",
                    created_thread.name,
                    created_thread.id,
                    message.id,
                )
            except Exception as e:
                logger.warning("Could not create PRIVATE thread for message %s: %s", message.id, e)
        elif isinstance(message.channel, discord.Thread):
            target_channel = message.channel

        # Provide a typing indicator while we think
        async with target_channel.typing():
            try:
                reply = await self._generate_reply(content, author=str(message.author))
            except Exception as e:
                logger.exception("Error generating reply: %s", e)
                reply = (
                    "I hit an unexpected error while generating a recommendation. "
                    "Please try again or provide a bit more detail about the client."
                )

        # Send the response
        try:
            logger.info(
                "Sending reply to %s %s (len=%d)",
                "thread" if isinstance(target_channel, discord.Thread) else "channel",
                getattr(target_channel, "id", None),
                len(reply or ""),
            )
            if isinstance(target_channel, discord.Thread):
                await target_channel.send(reply)
            else:
                await message.reply(reply, mention_author=False)
        except Exception:
            logger.exception("Failed to send reply to Discord")

    async def _generate_reply(self, user_text: str, *, author: str) -> str:
        messages = [
            {
                "role": "user",
                "content": (
                    "Question from agent '"
                    + author
                    + "':\n\n"
                    + user_text
                ),
            }
        ]
        text = await self._call_llm(messages)
        return text.strip() or "I couldn't produce a recommendation from the details provided."

    async def _call_llm(self, messages: List[dict]) -> str:
        # Small sleep helps ensure typing indicator is visible
        await asyncio.sleep(0.1)
        return await self.llm.complete(self.system_prompt, messages)

    # Legacy guidelines loading removed
