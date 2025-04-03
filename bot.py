import asyncio
from base64 import b64encode
from dataclasses import dataclass, field
from datetime import datetime as dt
import logging
from typing import Literal, Optional
from rag import fetch_past_vectors
from memory import update_user_memory,init_db

import discord
import httpx
import yaml
import re

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)


VISION_MODEL_TAGS = ("gpt-4", "claude-3", "gemini", "gemma", "pixtral", "mistral-small", "llava", "vision", "vl")
PROVIDERS_SUPPORTING_USERNAMES = ("openai", "x-ai")

EMBED_COLOR_COMPLETE = discord.Color.dark_green()
EMBED_COLOR_INCOMPLETE = discord.Color.orange()

STREAMING_INDICATOR = " ⚪"
EDIT_DELAY_SECONDS = 1

MAX_MESSAGE_NODES = 100

def remove_thinking_tags(response):
    # Remove <thinking> tags and their content
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    
    # Optionally, remove any leading or trailing whitespace
    response = response.strip()
    
    return response


def get_config(filename="config.yaml"):
    init_db()

    with open(filename, "r") as file:
        return yaml.safe_load(file)


cfg = get_config()

if client_id := cfg["client_id"]:
    logging.info(f"\n\nBOT INVITE URL:\nhttps://discord.com/api/oauth2/authorize?client_id={client_id}&permissions=412317273088&scope=bot\n")

intents = discord.Intents.default()
intents.message_content = True
activity = discord.CustomActivity(name=(cfg["status_message"] or "L3alim")[:128])
discord_client = discord.Client(intents=intents, activity=activity)

httpx_client = httpx.AsyncClient()

msg_nodes = {}
last_task_time = 0


@dataclass
class MsgNode:
    text: Optional[str] = None
    images: list = field(default_factory=list)

    role: Literal["user", "assistant"] = "assistant"
    user_id: Optional[int] = None

    has_bad_attachments: bool = False
    fetch_parent_failed: bool = False

    parent_msg: Optional[discord.Message] = None

    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


@discord_client.event
async def on_message(new_msg):
    global msg_nodes, last_task_time

    # Ignore messages from bots and those that don’t mention the bot
    if (not new_msg.channel.type == discord.ChannelType.private and discord_client.user not in new_msg.mentions) or new_msg.author.bot:
        return

    user_id = str(new_msg.author.id)
    username = new_msg.author.name
    user_message = new_msg.content.removeprefix(discord_client.user.mention).strip()

    # Load memory 
    relevant_messages,recent_messages = await fetch_past_vectors(user_message)

    # Build conversation history
    messages = [
        {
            "role": "system",
            "content": (
                f"You are El Metalico our mate and remember past conversations, but you don't make them up. You have memory,\
                  so act like a real friend. \
                 don't be so polite \
                 only the last message is important, other messages are just your memory, you don't have to mention them each time\
                    Avoid looking like an AI, no one should think you are an AI."
                "Messages follow this format: 'username: message'. You use the username to track who said what, but you never mention or use it in your replies. "
                "you have the last 5 messages for short memory followup and the first 5 other messages for you long term memory"
                "Your goal is to be a natural, real friend who keeps the conversation flowing."
            ),
        }
    ]

    for msg in recent_messages:
        messages.append({"role": "user", "content": f'(recent) {msg}'})

    for msg in relevant_messages:
        messages.append({"role": "user", "content": f'(context) {msg}' })  

    messages.append({"role": "user", "content": f"(latest) {username}: {user_message}"})

    print(messages)
    # Get API provider and model info
    provider, model = cfg["model"].split("/", 1)
    base_url = cfg["providers"][provider]["base_url"]
    api_key = cfg["providers"][provider].get("api_key", "sk-no-key-required")

    # Call AI API
    try:
        async with httpx.AsyncClient(timeout=50) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": cfg.get("max_tokens", 8000),
                    "temperature": cfg.get("temperature", 0.7),
                },
            )
            response.raise_for_status()
            data = response.json()

        # Process the AI's response
        reply_content = data["choices"][0]["message"]["content"]
        reply_content = remove_thinking_tags(reply_content)


        # Send response in chunks
        for chunk in [reply_content[i:i+2000] for i in range(0, len(reply_content), 2000)]:
            await new_msg.channel.send(chunk)

        # Update and save user memory
        await update_user_memory(user_id, username, user_message)
        await update_user_memory('you', 'EL METALICO', user_message)

    except httpx.HTTPStatusError as e:
        logging.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        await new_msg.channel.send("An error occurred while communicating with the AI.")
    except Exception as e:
        logging.exception("Unexpected error occurred")
        await new_msg.channel.send("An unexpected error occurred.")


async def main():
    await init_db()
    await discord_client.start(cfg["bot_token"])


asyncio.run(main())