import discord
import pytz
import json
from datetime import datetime
from utils.utils import analyze_text_for_personal_info, analyze_text_for_sensitive_info, analyze_text_for_inappropriate_content, send_deletion_notice_to_dm, save_deleted_message_info

BASE_PATH = 'data/blacklist.json'

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

async def on_message_analysis(message, client, LOG_CHANNEL_ID):
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
