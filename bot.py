import os
import discord
import requests

client = discord.Client(intents=discord.Intents.default())

API_URL = "https://api.groq.com/openai/v1/chat/completions"
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    prompt = message.content
    response = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
            "temperature": 0.7,
        },
    )

    reply = response.json()["choices"][0]["message"]["content"]
    await message.channel.send(reply)

client.run(DISCORD_TOKEN)

