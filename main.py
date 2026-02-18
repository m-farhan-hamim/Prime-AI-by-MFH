import discord
from discord import app_commands
from duckduckgo_search import DDGS
from aiohttp import web
import asyncio
import os

# --- CONFIGURATION ---
# 1. Get the Token
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# 2. Get the Allowed Server ID (Security Lock)
# If the variable is missing, it defaults to 0 (which means it won't work in any server, only DMs)
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
    """Starts a lightweight web server alongside the bot."""
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render provides the PORT environment variable
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌍 Web server running on port {port}")

# --- DISCORD BOT SETUP ---
class AnimeBot(discord.Client):
    def __init__(self):
        # We need default intents to see messages and users
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Sync commands and start the web server
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
    
    # 1. SECURITY CHECK (Server Lock)
    # If this is used in a server (Guild) AND that server ID doesn't match your private server ID...
    if interaction.guild and interaction.guild.id != ALLOWED_SERVER_ID:
        await interaction.response.send_message(
            "🚫 **Access Denied:** I am only authorized to work in Farhan's server.", 
            ephemeral=True # Only the user sees this error
        )
        return

    # 2. Acknowledge the command immediately (prevents timeout)
    await interaction.response.defer()

    # 3. DEFINE THE SEARCH LOGIC
    def run_duckduckgo():
        try:
            # Smart Prompt: We tell the AI to detect the language automatically
            prompt = (
                f"User Query: '{query}'. "
                f"Instructions: You are a helpful anime assistant. "
                f"1. Detect the language of the user's query (e.g., Bangla, English, Hindi). "
                f"2. Answer in that SAME language. "
                f"3. Provide the latest info/updates found."
            )
            # 'gpt-4o-mini' is usually the fastest and smartest free model on DDG
            results = DDGS().chat(prompt, model="gpt-4o-mini")
            return results
        except Exception as e:
            return f"❌ Jutsu failed (Error): {str(e)}"

    # 4. RUN SEARCH IN BACKGROUND (So bot doesn't freeze)
    response_text = await asyncio.to_thread(run_duckduckgo)

    # 5. FORMATTING THE MESSAGE
    footer = ""
    
    # If it is a Direct Message (DM), add your signature
    if interaction.guild is None:
        footer = "\n\n> *Bot by M. Farhan Hamim* 🇧🇩"

    # Discord has a 2000 character limit. We cut the text if it's too long.
    max_length = 2000 - len(footer) - 10
    if len(response_text) > max_length:
        response_text = response_text[:max_length] + "..."

    # 6. SEND THE RESULT
    await interaction.followup.send(f"{response_text}{footer}")

# --- START THE BOT ---
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ Error: DISCORD_TOKEN is missing from environment variables.")
    else:
        bot.run(DISCORD_TOKEN)
