import discord
import json

BLACKLIST_FILE = 'data/blacklist.json'

def load_blacklist():
    try:
        with open('blacklist.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"blacklisted_channels": []}

    if 'blacklisted_channels' not in data:
        return {"blacklisted_channels": []}
    
    return data

def save_blacklist(data):
    with open('blacklist.json', 'w', encoding='utf-8') as file:
        json.dump({"blacklisted_channels": data}, file, indent=4)

@tree.command(name='blacklist_add', description='Add a channel to the blacklist')
async def blacklist_add(interaction: discord.Interaction, channel: discord.TextChannel):
    blacklist = load_blacklist()
    if str(channel.id) in blacklist.get('blacklisted_channels', []):
        await interaction.response.send_message(f'Channel {channel.mention} is already blacklisted.', ephemeral=True)
    else:
        blacklist.get('blacklisted_channels', []).append(str(channel.id))
        save_blacklist(blacklist.get('blacklisted_channels', []))
        await interaction.response.send_message(f'Channel {channel.mention} has been added to the blacklist.', ephemeral=True)

@tree.command(name='blacklist_remove', description='Remove a channel from the blacklist')
async def blacklist_remove(interaction: discord.Interaction, channel: discord.TextChannel):
    blacklist = load_blacklist()
    if str(channel.id) not in blacklist['blacklisted_channels']:
        await interaction.response.send_message(f'Channel {channel.mention} is not blacklisted.', ephemeral=True)
    else:
        blacklist['blacklisted_channels'].remove(str(channel.id))
        save_blacklist(blacklist['blacklisted_channels'])
        await interaction.response.send_message(f'Channel {channel.mention} has been removed from the blacklist.', ephemeral=True)

@tree.command(name='blacklist_list', description='List all blacklisted channels')
async def blacklist_list(interaction: discord.Interaction):
    blacklist = load_blacklist()
    if not blacklist['blacklisted_channels']:
        await interaction.response.send_message('No channels are blacklisted.', ephemeral=True)
    else:
        channels = '\n'.join([f'<#{cid}>' for cid in blacklist['blacklisted_channels']])
        await interaction.response.send_message(f'Blacklisted channels:\n{channels}', ephemeral=True)