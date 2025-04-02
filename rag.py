import aiosqlite
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

DB_FILE = "server_memory.db"
model = SentenceTransformer("all-mpnet-base-v2")
index = faiss.IndexFlatL2(768)  # Vector size for MiniLM

async def fetch_past_vectors(new_message):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT user_id, messages FROM users")
        rows = await cursor.fetchall()

        if not rows:
            return "friendly", []  # Default personality, no messages

        messages = []
        for user_id, msg_json in rows:
            msg_list = json.loads(msg_json)
            for msg in msg_list:
                messages.append({"user": user_id, "content": msg})  # Store user info with messages

        if not messages:
            return "friendly", []

        # Encode stored messages into vectors
        stored_vectors = model.encode([msg["content"] for msg in messages])

        # Reset FAISS index to avoid duplicate data
        index.reset()
        index.add(np.array(stored_vectors))

        # Encode the new message
        new_vector = model.encode([new_message])

        # Search for 5 closest messages
        _, indices = index.search(new_vector, 10)

        # Retrieve relevant messages
        relevant_messages = [messages[i] for i in indices[0] if i < len(messages)]

    return relevant_messages
