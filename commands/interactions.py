import discord
import glob
from utils import create_embed_from_file, BASE_PATH

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
