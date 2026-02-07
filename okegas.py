import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import io
import datetime

# --- CONFIGURATION ---
TOKEN = 'MTQ2OTU2NTAwNTMxMjgyMzQxNw.GKa5CZ.hVgzxhoE1QKJAhq53QOnmTVozWEEwTJ9EDZ1X8'
BASE_URL = "https://kernelos.org"
API_URL = "https://kernelos.org/games/download.php?gen=1&id={}"

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Commands synced!")

bot = MyBot()

async def fetch_file(appid):
    # These are the Magic Headers that worked in your test!
    headers = {
        'User-Agent': 'kernelua-plugin/1.0.0 (Millennium)',
        'X-KernelUA': 'kernelua-plugin-1',
        'Accept': 'application/json',
        'X-Requested-With': 'kernelua-Plugin',
        'Origin': 'https://store.steampowered.com',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site'
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        print(f"Fetching API for AppID: {appid}")
        
        # Step 1: Get the Download Link
        try:
            async with session.get(API_URL.format(appid)) as resp:
                if resp.status != 200:
                    return None, f"API HTTP Error: {resp.status}"

                try:
                    data = await resp.json()
                except:
                    text = await resp.text()
                    return None, f"API Parse Error: {text[:100]}"

                # --- FIX: Check for 'url' directly instead of 'success' ---
                download_url = data.get('url')
                
                if not download_url:
                    # Only check for error if URL is missing
                    if 'error' in data:
                        return None, f"Server Error: {data['error']}"
                    return None, "Server returned no URL"
                
                # Fix relative URL path
                if download_url.startswith('/'):
                    download_url = BASE_URL + download_url

        except Exception as e:
            return None, f"Connection Error: {str(e)}"

        # Step 2: Download the File
        print(f"Downloading from: {download_url}")
        try:
            async with session.get(download_url) as file_resp:
                if file_resp.status != 200:
                    return None, f"Download HTTP Error: {file_resp.status}"
                
                # Try to get filename from headers
                content_disp = file_resp.headers.get("Content-Disposition", "")
                if "filename=" in content_disp:
                    filename = content_disp.split("filename=")[1].strip('"')
                else:
                    filename = f"{appid}.zip"

                file_bytes = await file_resp.read()
                return filename, io.BytesIO(file_bytes)
                
        except Exception as e:
            return None, f"Download Failed: {str(e)}"

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.tree.command(name="manifest", description="Generate a manifest file for a game by App ID")
@app_commands.describe(appid="The Steam App ID of the game")
async def manifest(interaction: discord.Interaction, appid: str):
    await interaction.response.defer(ephemeral=True)
    
    filename, file_data = await fetch_file(appid)
    
    if file_data and isinstance(file_data, io.BytesIO):
        discord_file = discord.File(fp=file_data, filename=filename)
        
        embed = discord.Embed(
            title=f"Game ID: {appid}",
            description="📜 Manifest generation completed.",
            color=0x9b59b6
        )
        embed.set_footer(text=f"By {bot.user.name} • {datetime.datetime.now().strftime('%I:%M %p')}")
        
        await interaction.followup.send(content="📎 Your manifest file is ready.", embed=embed, file=discord_file, ephemeral=True)
    else:
        error_msg = file_data if file_data else "Unknown error"
        await interaction.followup.send(f"❌ **Failed:** {error_msg}", ephemeral=True)

bot.run(TOKEN)
