import discord
import pytz
import json
from datetime import datetime
from utils.utils import analyze_text_for_personal_info, analyze_text_for_sensitive_info, analyze_text_for_inappropriate_content, send_deletion_notice_to_dm, save_deleted_message_info
import config

BASE_PATH = 'data/blacklist.json'

def load_blacklist():
    try:
        with open(BASE_PATH, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"blacklisted_channels": []}
    return data

def save_blacklist(data):
    with open(BASE_PATH, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)

async def on_message_analysis(message, client, LOG_CHANNEL_ID):
    if message.author.bot or str(message.guild.id) in config.EXCLUDED_GUILD_IDS:
        return

    blacklist = load_blacklist()
    if str(message.channel.id) in blacklist['blacklisted_channels']:
        return

    print(f"メッセージ受信: {message.content} from {message.author}")

    reasons = []
    delete_message = False

    personal_info_decision, personal_info_reasons = await analyze_text_for_personal_info(message.content)
    inappropriate_content_decision, inappropriate_content_reasons = await analyze_text_for_inappropriate_content(message.content)
    sensitive_info_decision, sensitive_info_reasons = await analyze_text_for_sensitive_info(message.content)

    # 真偽値がTrueの場合、関連する理由が空でないか確認
    if personal_info_decision and personal_info_reasons:
        delete_message = True
        reasons += personal_info_reasons
    if inappropriate_content_decision and inappropriate_content_reasons:
        delete_message = True
        reasons += inappropriate_content_reasons
    if sensitive_info_decision and sensitive_info_reasons:
        delete_message = True
        reasons += sensitive_info_reasons

    if delete_message:
        # 理由が空の場合のデフォルトメッセージを設定
        reason_text = ", ".join(reasons) if reasons else "特定の分析基準に違反しています"
        print(f"{reason_text}を削除します。")
        embed = discord.Embed(title="削除されたメッセージのログ", color=discord.Color.red())
        embed.add_field(name="送信者", value=message.author.mention, inline=False)
        embed.add_field(name="メッセージ内容", value=message.content, inline=False)
        embed.add_field(name="理由", value=reason_text, inline=False)
        embed.add_field(name="チャンネル", value=message.channel.mention, inline=False)
        embed.set_footer(text=f"メッセージID: {message.id} | 送信時刻: {datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S JST')}")

        await send_deletion_notice_to_dm(message.author, message.content, reason_text)
        try:
            await message.delete()
        except discord.NotFound:
            print(f"削除しようとしたメッセージが見つかりませんでした。Message ID: {message.id}")

        log_channel = client.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed)
            print("ログチャンネルに削除されたメッセージの情報を送信しました。")
    else:
        print("メッセージに問題はありません。")
