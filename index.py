from __future__ import annotations

import os
import asyncio
import logging

# Ensure a valid CA bundle is available to aiohttp/ssl on macOS. If the
# `certifi` package is installed, point SSL_CERT_FILE at its bundle so
# ssl verification won't fail when aiohttp connects to Discord/OpenAI.
try:
    import certifi

    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except Exception:
    # If certifi isn't installed, continue; the system certs may still work.
    pass

from config import Settings
from llm import LLMClient
from bot import DiscordBot


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)


async def main() -> None:
    settings = Settings.from_env()

    # Use only the SYSTEM_PROMPT_PREFIX as the Assistant instructions base.
    system_prompt = settings.system_prompt_prefix

    llm = LLMClient(api_key=settings.openai_api_key, model=settings.openai_model)

    bot = DiscordBot(
        allowed_channel_ids=settings.allowed_channel_ids,
        system_prompt=system_prompt,
        llm_client=llm,
        thread_name_template=settings.thread_name_template,
    )

    await bot.start(settings.discord_bot_token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
