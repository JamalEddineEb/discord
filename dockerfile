# Use the official Python image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements file to install dependencies
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot script into the container
COPY bot.py .

# Set environment variables for Discord token and Groq API key
ENV DISCORD_TOKEN=your_discord_bot_token_here
ENV GROQ_API_KEY=your_groq_api_key_here

# Run the bot script when the container starts
CMD ["python", "bot.py"]

