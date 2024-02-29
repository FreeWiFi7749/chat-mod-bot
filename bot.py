import discord
import asyncio
from config import DISCORD_TOKEN
from commands.message_analysis import on_message_analysis
from utils.utils import setup_openai

intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

@client.event
async def on_ready():
    print('------')
    print('Online! Details:')
    print(f"Bot Username: {client.user.name}")
    print(f"BotID: {client.user.id}")
    print('------')
    await tree.sync()
    await client.change_presence(activity= discord.Activity(name="起動中です…",type=discord.ActivityType.playing))
    setup_openai()
    await asyncio.sleep(60)
    while True:
     await client.change_presence(activity = discord.Activity(name="Moderating Chat Now", type=discord.ActivityType.watching))
     await asyncio.sleep(30)
     await client.change_presence(activity = discord.Activity(name="チャットを管理中", type=discord.ActivityType.watching))
     await asyncio.sleep(30)

@client.event
async def on_message(message):
    await on_message_analysis(message, client)

client.run(DISCORD_TOKEN)