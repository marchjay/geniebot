from __future__ import annotations

import asyncio
import time
import os
from typing import List, Optional

from openai import OpenAI
from storage import load_settings, save_settings


class LLMClient:
    """
    Assistant-backed LLM client.

    - Creates (or reuses) a single Assistant configured with SYSTEM_PROMPT_PREFIX as its
      instructions to keep per-request prompts small.
        - Assistant is always configured with the file_search tool enabled; you can manually
            attach files/vector stores to it in the OpenAI dashboard.
    - For each user query, creates a fresh Assistants Thread, posts the user's message(s),
      runs the Assistant, polls until completion, fetches the Assistant's latest reply, and
      deletes the thread to avoid cluttering memory.

    The complete(system_prompt, messages) signature is preserved for compatibility with the
    existing bot. The provided system_prompt is ignored in favor of the Assistant's
    configured instructions.
    """

    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

        # Load or create the Assistant configured with prefix instructions
        self.assistant_id = self._ensure_assistant()

    def _ensure_assistant(self) -> str:
        data = load_settings()  # uses .geniebot.json
        assistant_id = data.get("assistant_id")

        # Prepare instructions from SYSTEM_PROMPT_PREFIX env (authoritative in this project)
        prefix = os.getenv("SYSTEM_PROMPT_PREFIX", "").strip()
        if not prefix:
            prefix = "You are an assistant."

    # Always enable file_search on the Assistant so you can attach/upload files manually

        # If we have an existing assistant, try to update its instructions/model and
        # ensure vector store linkage if a guidelines file is provided.
        if assistant_id:
            try:
                updated = self.client.beta.assistants.update(
                    assistant_id=assistant_id,
                    model=self.model,
                    instructions=prefix,
                    tools=[{"type": "file_search"}],
                )
                return updated.id
            except Exception:
                # Fall through to create a new assistant if update fails
                pass

        # Create new assistant
        tools = [{"type": "file_search"}]

        assistant = self.client.beta.assistants.create(
            name="GenieBot Assistant",
            model=self.model,
            instructions=prefix,
            tools=tools,
        )
        data["assistant_id"] = assistant.id
        save_settings(data)
        return assistant.id

    async def complete(self, system_prompt: str, messages: List[dict]) -> str:
        # Build a fresh thread for this query so memory is isolated per conversation
        def run_sync_flow(user_messages: List[dict]) -> str:
            thread = self.client.beta.threads.create()

            # Add user messages to the thread (we expect one user message; support many just in case)
            for m in user_messages:
                if m.get("role") == "user":
                    content = m.get("content", "")
                    if content:
                        self.client.beta.threads.messages.create(
                            thread_id=thread.id,
                            role="user",
                            content=content,
                        )

            # Start a run
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id,
            )

            # Poll until complete
            while run.status in ("queued", "in_progress", "requires_action"):
                time.sleep(0.5)
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id,
                )

            # Fetch the latest assistant message
            text = ""
            try:
                msgs = self.client.beta.threads.messages.list(thread_id=thread.id, order="desc", limit=5)
                for msg in msgs.data:
                    if msg.role == "assistant":
                        # message content array may contain text parts
                        for part in msg.content:
                            if getattr(part, "type", None) == "text":
                                text = part.text.value
                                break
                        if text:
                            break
            except Exception:
                pass

            # Debug print of the assistant reply (length + snippet) for verification
            try:
                print(f"--- ASSISTANT REPLY (len={len(text)}) ---")
                print(text)
                print("--- END REPLY ---")
            except Exception:
                pass

            # Attempt to delete the thread to avoid clutter
            try:
                self.client.beta.threads.delete(thread_id=thread.id)
            except Exception:
                pass

            return text or ""

    # Removed verbose instruction/user payload printing as requested

        # Run the sync flow in a worker thread to avoid blocking the event loop
        return await asyncio.to_thread(run_sync_flow, messages)
        

