import discord
import openai
import json
import os
import asyncio
import pytz
from datetime import datetime
from config import api_keys

BASE_PATH = 'data/deleted_messages'

async def analyze_text(text: str, api_key: str, prompt: str) -> str:
    openai.api_key = api_key
    response = await asyncio.get_event_loop().run_in_executor(
        None, 
        lambda: openai.ChatCompletion.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
            max_tokens=1024
        )
    )
    content = response.choices[0].message['content']
    return content

def process_response(content):
    reasons = []
    if "削除が必要" in content:
        # レスポンスから具体的な理由を抽出
        split_content = content.split(":")
        if len(split_content) > 1:
            reason = split_content[1].strip()
            reasons.append(reason)
    return reasons

async def analyze_text_for_personal_info(text: str) -> (bool, list):
    print("テキスト分析を開始します。")

    prompt = "テキストに含まれている名前を分析して、以下の基準に基づいて判断してください。名前が実在する人物、特にDiscordサーバーに参加している可能性がある本名であれば「削除が必要:本名」と答えてください。公の人物や有名人、架空のキャラクター、一般的でない名前、またはユーモラスな愛称であれば、「削除不要」と答えてください。名前が完全に架空であるか、一般的に人名として認識されない場合は、「削除不要:架空の名前」または「削除不要:一般的ではない名前」と答えてください。判断が難しい場合は、「判断不能」と答えてください。"
    tasks = [analyze_text(text, api_key, prompt) for api_key in api_keys]
    results = await asyncio.gather(*tasks)
    reasons = []
    for result in results:
        reasons.extend(process_response(result))
    decision = any("削除が必要" in result for result in results)

    print("個人情報の分析結果:", decision, reasons)
    return decision, reasons

async def analyze_text_for_sensitive_info(text: str) -> (bool, list):
    #テキスト内の機密情報を分析し、削除が必要かどうかを判断します。
    print("機密情報のテキスト分析を開始します。")

    prompt = "テキスト内に電話番号、住所、メールアドレスなどの個人情報が含まれているかを分析します。これらの情報が含まれている場合は、「削除が必要」とし、含まれている情報の種類を明記します。これらに該当しない情報の場合は、「削除不要」とします。"
    tasks = [analyze_text(text, api_key, prompt) for api_key in api_keys]
    results = await asyncio.gather(*tasks)
    reasons = []
    for result in results:
        reasons.extend(process_response(result))
    decision = any("削除が必要" in result for result in results)

    print("個人情報の分析結果:", decision, reasons)
    return decision, reasons

async def analyze_text_for_inappropriate_content(text: str) -> (bool, list):
    #テキストが攻撃的、差別的、または性的に不適切な内容を含むかどうかを分析します。
    print("メッセージの安全性のテキスト分析を開始します。")

    prompt = "以下のテキストを分析してください。このテキストが攻撃的、差別的な言葉遣いを含む、または性的に不適切な内容であるかどうかを判断し、そのような内容が含まれている場合は「削除が必要」と応答してください。それ以外の場合は、「削除不要」と応答してください。また、含まれている不適切な内容の種類（攻撃的、差別的、性的に不適切）も明記してください。確信が持てない場合は、「判断不能」と応答してください。"
    tasks = [analyze_text(text, api_key, prompt) for api_key in api_keys]
    results = await asyncio.gather(*tasks)
    reasons = []
    for result in results:
        reasons.extend(process_response(result))
    decision = any("削除が必要" in result for result in results)

    print("不適切な内容の分析結果:", decision, reasons)
    return decision, reasons

async def main():
    text = "田中平八郎"
    # 各分析関数を実行
    personal_info_decision, personal_info_reasons = await analyze_text_for_personal_info(text)
    sensitive_info_decision, sensitive_info_reasons = await analyze_text_for_sensitive_info(text)
    inappropriate_content_decision, inappropriate_content_reasons = await analyze_text_for_inappropriate_content(text)

    # 「賛成」の数を集計（ここで修正）
    decisions = [personal_info_decision, sensitive_info_decision, inappropriate_content_decision]
    total_yes = decisions.count(True)  # True のみを集計

    # 全体の半数を超える場合に削除を推奨
    if total_yes > len(decisions) / 2:
        # 削除理由の集約（改善案）
        reasons = personal_info_reasons + sensitive_info_reasons + inappropriate_content_reasons
        reasons_text = ", ".join(reasons) if reasons else "多数決による判断"
        print(f"削除が必要: {reasons_text}, {reasons}")
        # 送信者のDMに削除通知を送信
        # ログチャンネルに削除されたメッセージの情報を送信
    else:
        print("削除不要")

if __name__ == "__main__":
    asyncio.run(main())

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
    openai.api_key = api_keys
