import discord
from discord import app_commands
from ddgs import DDGS  # Updated import to match the new package
from aiohttp import web
import asyncio
import os

# --- CONFIGURATION ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Security Lock: Defaults to 0 (DMs only) if the ID is missing
try:
    ALLOWED_SERVER_ID = int(os.getenv("ALLOWED_SERVER_ID", "0"))
except ValueError:
    print("⚠️ ALLOWED_SERVER_ID is not a valid number! Bot will only work in DMs.")
    ALLOWED_SERVER_ID = 0

# --- WEB SERVER (For Render Cron Jobs) ---
async def handle_ping(request):
    """Keeps the bot alive on Render."""
    return web.Response(text="Dattebayo! The bot is guarding the village. 🍃", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌍 Web server running on port {port}")

# --- DISCORD BOT SETUP ---
class AnimeBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        self.loop.create_task(start_web_server())
        print("⚡ Commands synced and Web Server started!")

    async def on_ready(self):
        print(f"Logged in as {self.user} 🍥")
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name="anime updates | /ai"
        ))

bot = AnimeBot()

# --- THE SLASH COMMAND ---
@bot.tree.command(name="ai", description="Ask about anime updates (Auto-detects Bangla/English/Hindi)")
@app_commands.describe(query="What do you want to know?")
async def ai_search(interaction: discord.Interaction, query: str):
    
    # 1. SECURITY CHECK
    if interaction.guild and interaction.guild.id != ALLOWED_SERVER_ID:
        await interaction.response.send_message(
            "🚫 **Access Denied:** I am only authorized to work in Farhan's server.", 
            ephemeral=True
        )
        return

    # 2. ACKNOWLEDGE
    await interaction.response.defer()

    # 3. SEARCH LOGIC
    def run_duckduckgo():
        try:
            # Smart Prompt with Language Detection
            prompt = (
                f"User Query: '{query}'. "
                f"Instructions: You are a helpful anime assistant. "
                f"1. Detect the language of the user's query (e.g., Bangla, English, Hindi). "
                f"2. Answer in that EXACT SAME language. "
                f"3. Provide the latest info/updates found."
            )
            # Using the DDGS class from the new package
            results = DDGS().chat(prompt, model="gpt-4o-mini")
            return results
        except Exception as e:
            return f"❌ Jutsu failed (Error): {str(e)}"

    # 4. EXECUTE
    response_text = await asyncio.to_thread(run_duckduckgo)

    # 5. FORMATTING
    footer = ""
    if interaction.guild is None: # DM Check
        footer = "\n\n> *Bot by M. Farhan Hamim* 🇧🇩"

    max_length = 2000 - len(footer) - 10
    if len(response_text) > max_length:
        response_text = response_text[:max_length] + "..."

    # 6. SEND
    await interaction.followup.send(f"{response_text}{footer}")

# --- START ---
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ Error: DISCORD_TOKEN is missing!")
    else:
        bot.run(DISCORD_TOKEN)
