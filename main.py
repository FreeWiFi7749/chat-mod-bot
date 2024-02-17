import discord
import openai
from dotenv import load_dotenv
import os
import asyncio
import pytz
from datetime import datetime
import json
import glob

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

class UserSelectMenu(discord.ui.Select):
    def __init__(self, user_ids, base_path, date):
        options = [
            discord.SelectOption(label=user_id, description="メッセージを表示", value=user_id)
            for user_id in user_ids
        ]
        super().__init__(placeholder="ユーザーIDを選択...", options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = self.values[0]
        files = glob.glob(f'{BASE_PATH}/{user_id}/*/*.json')
        embeds = [create_embed_from_file(fp) for fp in files]
        await interaction.response.edit_message(content='選択されたユーザーのメッセージ:', embeds=embeds, view=None)

BASE_PATH = 'deleted_messages' 

class DateSelectMenu(discord.ui.Select):
    def __init__(self, dates, base_path, user_id):
        self.user_id = user_id
        super().__init__(placeholder="日付を選択...", options=[
            discord.SelectOption(label=date, description="メッセージを表示", value=date) for date in dates
        ])
    
    async def callback(self, interaction: discord.Interaction):
        selected_date = self.values[0]
        files = glob.glob(f'{BASE_PATH}/{self.user_id}/{selected_date}/*.json')

        if not files:
            await interaction.response.send_message(f'選択された日付 {selected_date} にはメッセージがありません。', ephemeral=True)
            return
        
        embeds = [create_embed_from_file(file) for file in files]
        await interaction.response.edit_message(content='', embeds=embeds, view=None)

def create_embed_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        message_data = json.load(f)
    embed = discord.Embed(title="削除されたメッセージの詳細", color=discord.Color.red())
    embed.add_field(name="送信者ID", value=message_data["author_id"], inline=False)
    embed.add_field(name="メッセージ内容", value=message_data["message_content"], inline=False)
    embed.add_field(name="理由", value=message_data["reason"], inline=False)
    embed.add_field(name="削除時刻", value=message_data["timestamp"], inline=False)
    return embed

@tree.command(name='list_messages', description='指定された日付やユーザーIDに基づいて削除されたメッセージの一覧を表示します。')
async def list_messages(interaction: discord.Interaction, date: str = '', user_id: str = ''):
    base_path = 'deleted_messages'
    files = []
    await interaction.response.defer(ephemeral=True)
    
    # 日付とユーザーIDの両方が指定されている場合、ファイルのリストを取得します
    if date and user_id:
        user_date_path = os.path.join(base_path, user_id, date)
        files = glob.glob(f'{user_date_path}/*.json')
        if not files:
            await interaction.followup.send('指定された条件にマッチするメッセージは見つかりませんでした。', ephemeral=True)
            return
        embeds = [create_embed_from_file(file) for file in files[:25]]
        await interaction.followup.send(embeds=embeds, ephemeral=True)
        return

    # 日付のみが指定された場合
    if date:
        user_ids = extract_user_ids(base_path, date)
        await interaction.followup.send(
            'ユーザーIDを選択してください:',
            view=UserListView(user_ids, base_path, date),
            ephemeral=True
        )

    # ユーザーIDのみが指定された場合
    elif user_id:
        dates = extract_dates(base_path, user_id)
        await interaction.followup.send(
            '日付を選択してください:',
            view=DateListView(dates, base_path, user_id),
            ephemeral=True
        )

def create_embed_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        message_data = json.load(f)
    embed = discord.Embed(title="削除されたメッセージの詳細", color=discord.Color.red())
    embed.add_field(name="送信者ID", value=message_data["author_id"], inline=False)
    embed.add_field(name="メッセージ内容", value=message_data["message_content"], inline=False)
    embed.add_field(name="理由", value=message_data["reason"], inline=False)
    embed.add_field(name="削除時刻", value=message_data["timestamp"], inline=False)
    embed.add_field(name="チャンネル", value=f"{message_data['channel_name']} | {message_data['channel_id']}", inline=False)
    return embed

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

async def analyze_text_for_personal_info(text):
    print("テキスト分析を開始します。")
    loop = asyncio.get_running_loop()

    response = await loop.run_in_executor(
        None, 
        lambda: openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """
                    以下のテキストを分析してください。
                    このテキストに含まれている名前が、Discordサーバーに参加しているユーザーが誤って自分の本名を公開してしまった可能性があります。
                    名前が実際の人物の本名である場合は、「削除が必要:本名」と応答してください。
                    名前がフィクションのキャラクター名である場合は、「削除不要:キャラクター名」と、一般的ではない名前の場合は、「削除不要:一般的ではない名前」と応答してください。
                    確信が持てない場合は、「判断不能」と応答してください。
                    """                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            max_tokens=1024
        )
    )
    
    analysis_result = response.choices[0].message['content']
    print(f"名前のテキスト分析結果: {analysis_result}")
    return "削除が必要" in analysis_result

async def analyze_text_for_sensitive_info(text):
    loop = asyncio.get_running_loop()

    response = await loop.run_in_executor(
        None, 
        lambda: openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """
                    以下のテキストを分析してください。
                    このテキストに含まれている情報が電話番号、住所、またはメールアドレスであるかを判断し、それぞれの情報が含まれている場合は、「削除が必要」と応答してください。
                    含まれている情報がこれらのカテゴリーに該当しない場合は、「削除不要」と応答してください。
                    また、含まれている情報の種類（電話番号、住所、メールアドレス）も明記してください。
                    確信が持てない場合は、「判断不能」と応答してください。
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
    print(f"電話番号等のテキスト分析結果: {analysis_result}")
    return "削除が必要" in analysis_result

async def analyze_text_for_inappropriate_content(text):
    loop = asyncio.get_running_loop()

    response = await loop.run_in_executor(
        None, 
        lambda: openai.ChatCompletion.create(
            model="gpt-4",
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

@client.event
async def on_message(message):
    if message.author.bot:
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

client.run(DISCORD_TOKEN)