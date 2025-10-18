# GenieBot (Discord + OpenAI Assistants API)

GenieBot is a Discord bot that answers insurance carrier selection questions. It uses the OpenAI Assistants API with a persistent Assistant configured by your `SYSTEM_PROMPT_PREFIX`, and creates a private Discord thread per question so conversations stay tidy and scoped.

## What’s new

- Migrated from Chat Completions to the Assistants API
- Persistent Assistant whose instructions come from `SYSTEM_PROMPT_PREFIX`
- Per-message private Discord thread creation (author is invited automatically)
- Channel access control and a `/genie_channel` admin command
- File Search tool enabled on the Assistant; attach files/vector stores via OpenAI dashboard
- Clean per-question memory: new Assistants Thread each time, then deleted

## Requirements

- Python 3.10+
- A Discord application/bot token with Message Content Intent enabled
- An OpenAI API key

## Quick start (macOS/Linux)

1) Create a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate
```

2) Install dependencies

```bash
pip install -r requirements.txt
```

3) Configure environment

Create a `.env` file in the repo root and set at least:

```env
DISCORD_BOT_TOKEN=your-discord-bot-token
OPENAI_API_KEY=sk-...
# Optional
OPENAI_MODEL=gpt-4o-mini
DISCORD_ALLOWED_CHANNEL_IDS=123456789012345678,234567890123456789
SYSTEM_PROMPT_PREFIX=You are a helpful assistant specialized in life-insurance carrier selection.
THREAD_NAME_TEMPLATE=genie-{author}-{id}
```

Notes
- `DISCORD_ALLOWED_CHANNEL_IDS` empty means “allow all channels.” Otherwise, only those channels (or threads under them) are allowed. You can also set the channel at runtime via the `/genie_channel` command (persisted).
- `THREAD_NAME_TEMPLATE` supports placeholders: `{author}`, `{id}`, `{channel}`, `{user_id}`. Names are sanitized and truncated to ~100 chars.
- `SYSTEM_PROMPT_PREFIX` can be literal prompt text or a filesystem path to a text file (see Prompt source below).

4) Run the bot

```bash
python index.py
```

Invite the bot to your server with permission to read/send messages and create private threads. Ensure Message Content Intent is enabled in the Developer Portal and in code (see `bot.py`).

## Prompt source: SYSTEM_PROMPT_PREFIX

The Assistant’s instructions are set at startup from the `SYSTEM_PROMPT_PREFIX` environment variable via a small heuristic in `config.py`:

- If the value looks like a short, plausible file path and exists, its contents are loaded.
- If it’s long or multiline, or the path check fails, the value is used as literal instructions.

Update `SYSTEM_PROMPT_PREFIX` and restart the bot to change the Assistant’s instructions. Instructions are not passed per-run; they live on the persistent Assistant.

## Discord behavior

- The bot listens in allowed channels (and any threads under them). If no allow-list is set, it listens everywhere it has access.
- For each non-bot message in a text channel, the bot creates a private thread from that message, invites the author, and replies there.
- If you post inside an existing thread, the bot replies in that thread.
- Private threads auto-archive (24h by default). The bot doesn’t force-close threads.

Admin control
- Use `/genie_channel` to set the single channel where Genie listens/replies (admin only). This is persisted in `.geniebot.json`.

## Assistants API integration

At startup (`index.py` → `llm.py`):
1) Ensure or create a persistent Assistant with:
   - `model` = `OPENAI_MODEL` (default `gpt-4o-mini`)
   - `instructions` = `SYSTEM_PROMPT_PREFIX`
   - `tools` = `[ { "type": "file_search" } ]`
   The assistant id is cached in `.geniebot.json`.
2) For each Discord message:
   - Create a fresh Assistants Thread
   - Add the user’s message
   - Create a Run for the configured Assistant
   - Poll until complete
   - Read the latest assistant message from the thread
   - Delete the thread (keeps memory isolated per question)

Retrieval/file search
- File Search is enabled on the Assistant. Attach files or a vector store to this Assistant in the OpenAI dashboard to let it ground responses. No local upload is performed by the bot.

## Repository layout

- `index.py` – Entrypoint; loads settings, ensures Assistant, starts Discord client
- `bot.py` – Discord client and message flow; creates private threads; `/genie_channel`
- `llm.py` – Assistants client; ensure/update Assistant; per-question Thread/Run flow
- `config.py` – Loads `.env`; SYSTEM_PROMPT_PREFIX literal-or-path heuristic; thread name template
- `storage.py` – Reads/writes `.geniebot.json` for persistent ids/settings
- `requirements.txt` – Python dependencies
- `test.py` – Utility for inspecting OpenAI files (id/content preview)

## Observability and logs

- General logs are INFO-level via `logging.basicConfig` in `index.py`.
- `llm.py` prints a short preview of each Assistant reply (length + first ~500 chars) to stdout for verification.
- Discord actions (thread creation, send targets) are logged at INFO.

## Troubleshooting

- Bot doesn’t respond
  - Verify the bot has permission in the channel, and the channel is allowed (env or `/genie_channel`).
  - Ensure Message Content Intent is enabled in the Discord Developer Portal and the code uses `intents.message_content = True`.

- OpenAI errors
  - Confirm `OPENAI_API_KEY` and `OPENAI_MODEL`. Temporary network issues will surface as exceptions; check console logs.

- Prompt file path vs literal
  - Very long or multiline `SYSTEM_PROMPT_PREFIX` values are treated as literal text. If you intended a path, shorten the path and ensure the file exists.

- SSL/certificates on macOS
  - `index.py` points `SSL_CERT_FILE` to `certifi`’s bundle if available to avoid TLS issues with Discord/OpenAI.

- Discord 2000-character limit
  - Extremely long responses may fail to send. Current version posts directly without chunking/attachments. If you hit this, shorten the prompt or ask for a concise answer. Attachment fallback can be added as a future enhancement.

## Changing behavior

- Update `.env` and restart:
  - `SYSTEM_PROMPT_PREFIX` to change Assistant behavior
  - `DISCORD_ALLOWED_CHANNEL_IDS` or use `/genie_channel`
  - `THREAD_NAME_TEMPLATE` to alter private thread naming

## Notes

- You can optionally attach files/vector stores to the Assistant in the OpenAI dashboard. The bot will use them via File Search automatically.
- The project stores its Assistant id and settings in `.geniebot.json` (created on first run).

---

Happy automating! If you’d like extras (message chunking/attachments, admin diagnostics, or toggling reply previews), they can be added with small changes to `bot.py`/`llm.py`.
