# GenieBot (Discord AI Assistant for Carrier Selection)

GenieBot is a Discord chatbot that helps agents choose the best life-insurance carrier for a client's specific situation. The bot uses the OpenAI Assistants API with a persistent Assistant that you configure via `SYSTEM_PROMPT_PREFIX`. You can attach files/vector stores to the Assistant in the OpenAI dashboard; the bot has file search enabled.

## Features

- Python (discord.py) bot with AI answers via OpenAI
- Restrict responses to specific Discord channels
- Private Discord threads per question (only visible to invited members/mods)
- File search enabled on the Assistant (attach files via OpenAI dashboard)
- Simple, concise carrier recommendations with rationale

## Prerequisites

- Python 3.10+
- A Discord bot application and bot token
  - In the Discord Developer Portal, enable "MESSAGE CONTENT INTENT"
- An OpenAI API key

## Setup

1. Clone or open this folder.
2. Create a virtual environment (recommended).
3. Install dependencies.
4. Configure environment variables.
5. Run the bot.

### 1) Virtual environment (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```powershell
pip install -r requirements.txt
```

### 3) Configure environment variables

Copy `.env.example` to `.env` and fill in values.

- `DISCORD_BOT_TOKEN`: your bot token
- `DISCORD_ALLOWED_CHANNEL_IDS`: comma-separated channel IDs (or leave blank to allow all)
- `OPENAI_API_KEY`: your OpenAI API key
- `OPENAI_MODEL`: optional, defaults to `gpt-4o-mini`
- `SYSTEM_PROMPT_PREFIX`: optional, a short, high-level role prompt

### 4) Provide guidelines (optional)

Attach your underwriting guides and medication lists to the Assistant in the OpenAI dashboard. The bot is configured with file search enabled and will use attached knowledge when responding.

### 5) Run the bot

```powershell
python index.py
```

The bot must be invited to your server with appropriate permissions (read/send messages). Ensure "Message Content Intent" is enabled in the Developer Portal and in code we set `intents.message_content = True`.

## How it works

- Entry point: `index.py`
- Bot client: `bot.py`
- Config/env: `config.py`
- OpenAI Assistants client: `llm.py` (creates/updates a persistent Assistant with `SYSTEM_PROMPT_PREFIX`, file_search enabled)

## Customization

- Add more channel rules or per-channel prompts in `bot.py` as needed.
-- Update `SYSTEM_PROMPT_PREFIX` and restart to change Assistant instructions. For per-query overrides, add run-level instructions in `llm.py`.
- Swap the LLM provider by replacing `LLMClient` implementation.

## Troubleshooting

- If imports fail, verify your virtual env is activated.
- If the bot doesn't respond, check channel IDs and that the bot has permissions.
- If OpenAI calls fail, verify the API key and model.
