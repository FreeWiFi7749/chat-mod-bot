import discord
import openai
import json
import os
import asyncio
import pytz
from datetime import datetime
from config import OPENAI_API_KEY

BASE_PATH = 'data/deleted_messages'

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


def setup_openai():
    openai.api_key = OPENAI_API_KEY