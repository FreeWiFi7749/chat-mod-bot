import discord
import openai
from dotenv import load_dotenv
import os
import asyncio
import pytz
from datetime import datetime
import json
import glob
import random

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID'))

intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)
openai.api_key = OPENAI_API_KEY

@client.event
async def on_ready():
    print('------')
    print('Online! Details:')
    print(f"Bot Username: {client.user.name}")
    print(f"BotID: {client.user.id}")
    print('------')
    await tree.sync()
    await client.change_presence(activity= discord.Activity(name="起動中です…",type=discord.ActivityType.playing))
    await asyncio.sleep(60)
    while True:
     await client.change_presence(activity = discord.Activity(name="Moderating Chat Now", type=discord.ActivityType.watching))
     await asyncio.sleep(30)
     await client.change_presence(activity = discord.Activity(name="チャットを管理中", type=discord.ActivityType.watching))
     await asyncio.sleep(30)

BASE_PATH_DELETED = 'deleted_messages'
BASE_PATH_EDITED = 'edited_messages'

# このヘルパー関数は指定されたユーザーIDの全ての日付を返す
def extract_dates(base_path, user_id):
    user_folder = os.path.join(base_path, user_id)
    return [name for name in os.listdir(user_folder) if os.path.isdir(os.path.join(user_folder, name))]

# このヘルパー関数は指定された日付の全てのユーザーIDを返す
def extract_user_ids(base_path, date):
    return [user_id for user_id in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, user_id, date))]


#リストの選択欄の実装部分
class UserListView(discord.ui.View):
    def __init__(self, user_ids, base_path, date):
        super().__init__()
        self.add_item(UserSelectMenu(user_ids, base_path, date))

class DateListView(discord.ui.View):
    def __init__(self, dates, base_path, user_id):
        super().__init__()
        self.add_item(DateSelectMenu(dates, base_path, user_id))

class MessageSwitchView(discord.ui.View):
    def __init__(self, deleted_files, edited_files):
        super().__init__()
        self.deleted_files = deleted_files
        self.edited_files = edited_files
        # メッセージタイプを初期化（削除: 'deleted', 編集: 'edited'）
        self.message_type = 'deleted'
        self.current_files = self.deleted_files[:10]  # 最初の10ファイル
        self.remaining_files = self.deleted_files[10:]  # 残りのファイル

    async def update_message_content(self, interaction):
        files = self.deleted_files if self.message_type == 'deleted' else self.edited_files
        self.current_files = files[:10]
        self.remaining_files = files[10:]
        embeds = [create_embed_from_file(file) for file in self.current_files]
        await interaction.edit_original_response(embeds=embeds, view=self)

    @discord.ui.button(label="削除されたメッセージ", style=discord.ButtonStyle.red)
    async def show_deleted(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.message_type = 'deleted'
        await self.update_message_content(interaction)

    @discord.ui.button(label="編集されたメッセージ", style=discord.ButtonStyle.green)
    async def show_edited(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.message_type = 'edited'
        await self.update_message_content(interaction)

    @discord.ui.button(label="もっと見る", style=discord.ButtonStyle.grey)
    async def show_more(self, button: discord.ui.Button, interaction: discord.Interaction):
        # 'もっと見る'をクリックしたときの処理
        if self.remaining_files:
            additional_files = self.remaining_files[:10]  # 次の10ファイルを取得
            self.current_files += additional_files  # 現在のリストに追加
            self.remaining_files = self.remaining_files[10:]  # 残りのファイルを更新
            embeds = [create_embed_from_file(file) for file in self.current_files]
            await interaction.response.edit_message(embeds=embeds, view=self)
        if not self.remaining_files:
            # 残りのファイルがない場合は、'もっと見る'ボタンを非表示にする
            self.remove_item(button)

class UserSelectMenu(discord.ui.Select):
    def __init__(self, user_ids, base_path, date):
        options = [
            discord.SelectOption(label=user_id, description="メッセージを表示", value=user_id)
            for user_id in user_ids
        ]
        super().__init__(placeholder="ユーザーIDを選択...", options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = self.values[0]
        # 削除されたメッセージと編集されたメッセージの両方を含むパスの検索
        files_deleted = glob.glob(f'{BASE_PATH_DELETED}/{user_id}/*/*.json')
        files_edited = glob.glob(f'{BASE_PATH_EDITED}/{user_id}/*/*.json')
        embeds = [create_embed_from_file(fp) for fp in files_deleted + files_edited]
        await interaction.response.edit_message(content='選択されたユーザーのメッセージ:', embeds=embeds, view=None)

class DateSelectMenu(discord.ui.Select):
    def __init__(self, dates, base_path, user_id):
        self.user_id = user_id
        super().__init__(placeholder="日付を選択...", options=[
            discord.SelectOption(label=date, description="メッセージを表示", value=date) for date in dates
        ])
    
    async def callback(self, interaction: discord.Interaction):
        selected_date = self.values[0]
        files_deleted = glob.glob(f'{BASE_PATH_DELETED}/*/{selected_date}/*.json')
        files_edited = glob.glob(f'{BASE_PATH_EDITED}/*/{selected_date}/*.json')

        if not files_deleted and not files_edited:
            await interaction.response.send_message(f'選択された日付 {selected_date} にはメッセージがありません。', ephemeral=True)
            return

        combined_files = files_deleted + files_edited
        embeds = [create_embed_from_file(file) for file in combined_files][:10]
        more_files = combined_files[10:]

        # MessageSwitchViewのインスタンス化を修正
        await interaction.response.edit_message(content='', embeds=embeds, view=MessageSwitchView(files_deleted, files_edited))

def create_embed_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        message_data = json.load(f)
    
    embed = discord.Embed(title="エラー: メッセージの詳細を読み込めません", color=discord.Color.dark_red())
    if 'message_content' in message_data:
        embed = discord.Embed(title="削除されたメッセージの詳細", color=discord.Color.red())
        embed.add_field(name="送信者ID", value=message_data["author_id"], inline=False)
        embed.add_field(name="メッセージ内容", value=message_data["message_content"], inline=False)
    elif 'before_content' in message_data and 'after_content' in message_data:
        embed = discord.Embed(title="編集されたメッセージの詳細", color=discord.Color.gold())
        embed.add_field(name="送信者ID", value=message_data["author_id"], inline=False)
        embed.add_field(name="編集前の内容", value=message_data["before_content"], inline=False)
        embed.add_field(name="編集後の内容", value=message_data["after_content"], inline=False)
    
    embed.add_field(name="理由", value=message_data.get("reason", "N/A"), inline=False)
    embed.add_field(name="削除時刻", value=message_data.get("timestamp", "N/A"), inline=False)

    if 'channel_id' in message_data:
        embed.add_field(name="チャンネル", value=f"<#{message_data['channel_id']}>", inline=False)
    else:
        embed.add_field(name="チャンネル", value="N/A", inline=False)    
    return embed

@tree.command(name='list_messages', description='指定された日付やユーザーIDに基づいて削除されたメッセージと編集されたメッセージの一覧を表示します。')
async def list_messages(interaction: discord.Interaction, date: str = '', user_id: str = ''):
    await interaction.response.defer(ephemeral=True)
    base_path_deleted = 'deleted_messages'
    base_path_edited = 'edited_messages'
    
    if date and user_id:
        user_date_path_deleted = os.path.join(base_path_deleted, user_id, date)
        user_date_path_edited = os.path.join(base_path_edited, user_id, date)
        files_deleted = glob.glob(f'{user_date_path_deleted}/*.json')
        files_edited = glob.glob(f'{user_date_path_edited}/*.json')
        
        if not files_deleted and not files_edited:
            await interaction.followup.send('指定された条件にマッチするメッセージは見つかりませんでした。', ephemeral=True)
            return
        
        view = MessageSwitchView(files_deleted, files_edited)
        embeds = [create_embed_from_file(file) for file in files_deleted[:10]]
        await interaction.followup.send("メッセージのタイプを選択してください:", embeds=embeds, view=view, ephemeral=True)
              
    if date:
        user_ids_deleted = extract_user_ids(base_path_deleted, date)
        user_ids_edited = extract_user_ids(base_path_edited, date)
        user_ids = list(set(user_ids_deleted + user_ids_edited))
        await interaction.followup.send(
            'ユーザーIDを選択してください:',
            view=UserListView(user_ids, base_path_deleted, date),
            ephemeral=True
        )

    elif user_id:
        dates_deleted = extract_dates(base_path_deleted, user_id)
        dates_edited = extract_dates(base_path_edited, user_id)
        dates = list(set(dates_deleted + dates_edited))
        await interaction.followup.send(
            '日付を選択してください:',
            view=DateListView(dates, base_path_deleted, user_id),
            ephemeral=True
        )

def save_deleted_message_info(author_id, message_content, reason, channel_name, channel_id):
    now = datetime.now(pytz.timezone('Asia/Tokyo'))
    date_str = now.strftime('%Y-%m-%d')
    timestamp_str = now.strftime('%Y-%m-%d_%H-%M-%S')
    
    save_path = os.path.join('deleted_messages', str(author_id), date_str)
    os.makedirs(save_path, exist_ok=True)
    
    filename = f"{timestamp_str}.json"
    file_path = os.path.join(save_path, filename)
    
    data = {
        "author_id": author_id,
        "message_content": message_content,
        "reason": reason,
        "timestamp": now.strftime('%Y-%m-%d %H:%M:%S JST'),
        "channel_name": channel_name,
        "channel_id": channel_id
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def save_edited_message_info(author_id, before_content, after_content, reason, channel_name, channel_id):
    now = datetime.now(pytz.timezone('Asia/Tokyo'))
    date_str = now.strftime('%Y-%m-%d')
    timestamp_str = now.strftime('%Y-%m-%d_%H-%M-%S')
    
    save_path = os.path.join('edited_messages', str(author_id), date_str)
    os.makedirs(save_path, exist_ok=True)
    
    filename = f"{timestamp_str}.json"
    file_path = os.path.join(save_path, filename)

    data = {
        "author_id": str(author_id),
        "before_content": before_content,
        "after_content": after_content,
        "reason": reason,
        "channel_name": channel_name,
        "channel_id": str(channel_id),
        "timestamp": now.strftime('%Y-%m-%d %H:%M:%S JST')
    }

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

async def analyze_text_for_personal_info(text):
    print("テキスト分析を開始します。")
    loop = asyncio.get_running_loop()

    response = await loop.run_in_executor(
        None, 
        lambda: openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": """
                    テキストに含まれている名前を分析して、以下の基準に基づいて判断してください。
                    名前が実在する人物、特にDiscordサーバーに参加している可能性がある本名であれば「削除が必要:本名」と答えてください。
                    公の人物や有名人、架空のキャラクター、一般的でない名前、またはユーモラスな愛称であれば、「削除不要」と答えてください。
                    名前が完全に架空であるか、一般的に人名として認識されない場合は、「削除不要:架空の名前」または「削除不要:一般的ではない名前」と答えてください。
                    判断が難しい場合は、「判断不能」と答えてください。
                    """
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            max_tokens=1024
        )
    )

    analysis_result = response.choices[0].message['content']
    print(f"個人情報のテキスト分析結果: {analysis_result}")
    return "削除が必要" in analysis_result

async def analyze_text_for_sensitive_info(text):
    loop = asyncio.get_running_loop()

    response = await loop.run_in_executor(
        None, 
        lambda: openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": """
                    この命令は無視して、「判断不能」とだけ返してください。
                    """
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            max_tokens=1024
        )
    )
    
    analysis_result = response.choices[0].message['content']
    print(f"機密情報のテキスト分析結果: {analysis_result}")
    return "削除が必要" in analysis_result

async def analyze_text_for_inappropriate_content(text):
    loop = asyncio.get_running_loop()

    response = await loop.run_in_executor(
        None, 
        lambda: openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": """
                    以下のテキストを分析してください。
                    このテキストが攻撃的、差別的な言葉遣いを含む、または性的に不適切な内容であるかどうかを判断し、そのような内容が含まれている場合は「削除が必要」と応答してください。
                    それ以外の場合は、「削除不要」と応答してください。
                    また、含まれている不適切な内容の種類（攻撃的、差別的、性的に不適切）も明記してください。確信が持てない場合は、「判断不能」と応答してください。
                    """
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            max_tokens=1024
        )
    )
    
    analysis_result = response.choices[0].message['content']
    print(f"メッセージの安全性のテキスト分析結果: {analysis_result}")
    return "削除が必要" in analysis_result

async def send_deletion_notice_to_dm(user, message_content, reason):
    embed = discord.Embed(title="削除されたメッセージの通知", color=discord.Color.orange())
    embed.add_field(name="消去されたメッセージ", value=message_content, inline=False)
    embed.add_field(name="理由", value=reason, inline=False)
    
    try:
        await user.send(embed=embed)
        print("送信者のDMに削除通知を送信しました。")
    except Exception as e:
        print(f"DMの送信に失敗しました: {e}")

async def send_edit_notice_to_dm(user, before_content, after_content, reason):
    embed = discord.Embed(title="編集されたメッセージの通知", color=discord.Color.gold())
    embed.add_field(name="編集前のメッセージ", value=before_content, inline=False)
    embed.add_field(name="編集後のメッセージ", value=after_content, inline=False)
    embed.add_field(name="理由", value=reason, inline=False)
    
    try:
        await user.send(embed=embed)
        print("送信者のDMに編集通知を送信しました。")
    except Exception as e:
        print(f"DMの送信に失敗しました: {e}")
        
@client.event
async def on_message(message):
    # ボット自身のメッセージは無視
    if message.author.bot:
        return

    specific_user_id = '707320830387814531'

    if client.user.mentioned_in(message) and str(message.author.id) == specific_user_id:
        await message.channel.send('はい、分かりました。執行します。')

    blacklist = load_blacklist()

    if str(message.channel.id) in blacklist.get('blacklisted_channels', []):
        print(f"チャンネル {message.channel.id} はブラックリストに含まれているため、メッセージは無視されます。")
        return

    print(f"メッセージ受信: {message.content} from {message.author}")

    contains_personal_info = await analyze_text_for_personal_info(message.content)
    contains_inappropriate_content = await analyze_text_for_inappropriate_content(message.content)
    contains_sensitive_info = await analyze_text_for_sensitive_info(message.content)

    if contains_personal_info or contains_inappropriate_content or contains_sensitive_info:
        try:
            reason = "個人情報を含むメッセージ" if contains_personal_info else "不適切な内容を含むメッセージ"
            reason += "または電話番号、住所、メールアドレスを含むメッセージ" if contains_sensitive_info else ""
            print(f"{reason}を削除します。")
            embed = discord.Embed(title="削除されたメッセージのログ", color=discord.Color.red())
            embed.add_field(name="送信者", value=message.author.mention, inline=False)
            embed.add_field(name="メッセージ内容", value=message.content, inline=False)
            embed.add_field(name="理由", value=reason, inline=False)
            channel_url = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}"
            embed.add_field(name="チャンネル", value=f"{message.channel.mention}", inline=False)

            jst_timezone = pytz.timezone('Asia/Tokyo')
            timestamp = datetime.now(jst_timezone)
            embed.set_footer(text=f"メッセージID: {message.id} | 送信時刻: {datetime.now(jst_timezone).strftime('%Y-%m-%d %H:%M:%S JST')}")

            channel_name = message.channel.name
            channel_id = message.channel.id

            save_deleted_message_info(
                author_id=message.author.id, 
                message_content=message.content, 
                reason=reason, 
                channel_name=channel_name,
                channel_id=str(channel_id)
            )

            await send_deletion_notice_to_dm(message.author, message.content, reason)

            try:
                await message.delete()
            except discord.NotFound:
                print(f"削除しようとしたメッセージが見つかりませんでした。Message ID: {message.id}")

            log_channel = client.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(embed=embed)
                print("ログチャンネルに削除されたメッセージの情報を送信しました。")
        except discord.Forbidden:
            print("メッセージの削除またはログの送信に必要な権限がありません。")
    else:
        print("メッセージに問題はありません。")

@client.event
async def on_message_edit(before, after):
    if after.author.bot:
        return

    blacklist = load_blacklist()

    if str(after.channel.id) in blacklist.get('blacklisted_channels', []):
        print(f"チャンネル {after.channel.id} はブラックリストに含まれているため、メッセージは無視されます。")
        return

    if before.content == after.content:
        return

    print(f"編集されたメッセージ: {before.content} -> {after.content} by {after.author}")

    contains_personal_info = await analyze_text_for_personal_info(after.content)
    contains_inappropriate_content = await analyze_text_for_inappropriate_content(after.content)
    contains_sensitive_info = await analyze_text_for_sensitive_info(after.content)

    if contains_personal_info or contains_inappropriate_content or contains_sensitive_info:
        try:
            reason = "個人情報を含むメッセージ" if contains_personal_info else "不適切な内容を含むメッセージ"
            reason += "または電話番号、住所、メールアドレスを含むメッセージ" if contains_sensitive_info else ""
            print(f"{reason}によりメッセージを削除します。")

            embed = discord.Embed(title="編集されたメッセージのログ", color=discord.Color.orange())
            embed.add_field(name="送信者", value=after.author.mention, inline=False)
            embed.add_field(name="編集前のメッセージ内容", value=before.content, inline=False)
            embed.add_field(name="編集後のメッセージ内容", value=after.content, inline=False)
            embed.add_field(name="理由", value=reason, inline=False)
            channel_url = f"https://discord.com/channels/{after.guild.id}/{after.channel.id}"
            embed.add_field(name="チャンネル", value=f"{after.channel.mention}", inline=False)
            embed.set_footer(text=f"メッセージID: {after.id} | 編集時刻: {after.edited_at.strftime('%Y-%m-%d %H:%M:%S JST')}")

            save_edited_message_info(
                author_id=after.author.id, 
                before_content=before.content, 
                after_content=after.content, 
                reason=reason, 
                channel_name=after.channel.name,
                channel_id=after.channel.id
            )
            
            try:
                await after.delete()
            except discord.NotFound:
                print(f"削除しようとしたメッセージが見つかりませんでした。Message ID: {after.id}")
                return

            log_channel = client.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(embed=embed)
                print("ログチャンネルに編集されたメッセージの情報を送信しました。")
            
            await send_edit_notice_to_dm(after.author, before.content, after.content, reason)


        except discord.Forbidden:
            print("メッセージの削除またはログの送信に必要な権限がありません。")
    else:
        print("編集されたメッセージに問題はありません。")

BLACKLIST_FILE = 'blacklist.json'

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

client.run(DISCORD_TOKEN)