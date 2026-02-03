# Point_system.py
import discord
from discord import app_commands
import gspread
import os, json, base64
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime


# ---------- Google Sheet (เฉพาะ Point System) ----------
def get_point_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    base64_json = os.getenv("GOOGLE_SHEETS_JSON_BASE64")
    sheet_url = os.getenv("POINT_SHEET_URL")

    if not base64_json or not sheet_url:
        raise ValueError("Point system sheet env not found")

    creds_dict = json.loads(
        base64.b64decode(base64_json).decode("utf-8")
    )
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    return client.open_by_url(sheet_url)


# ---------- Slash Command ----------
def setup_point_system(bot: discord.Client):

    @bot.tree.command(
        name="goodpoint",
        description="เพิ่ม / ลด แต้มเด็กดี"
    )
    @app_commands.describe(
        method="เลือกเพิ่มหรือลดแต้ม",
        user="คนที่ต้องการปรับแต้ม"
    )
    @app_commands.choices(method=[
        app_commands.Choice(name="➕ เพิ่มแต้ม", value="add"),
        app_commands.Choice(name="➖ ลดแต้ม", value="remove")
    ])
    async def goodpoint(
        interaction: discord.Interaction,
        method: app_commands.Choice[str],
        user: discord.Member
    ):
        sheet = get_point_sheet()
        point_ws = sheet.worksheet("Point")
        history_ws = sheet.worksheet("History")

        users = point_ws.get("C2:C")
        target_row = None

        for i, row in enumerate(users, start=2):
            if row and row[0] == user.mention:
                target_row = i
                break

        if not target_row:
            await interaction.response.send_message(
                f"❌ ไม่พบ {user.mention} ในระบบแต้มเด็กดี",
                ephemeral=True
            )
            return

        current_point = float(point_ws.cell(target_row, 4).value or 0)
        delta = 0.5

        if method.value == "add":
            new_point = current_point + delta
            point_ws.update_cell(target_row, 4, new_point)
            add_val, remove_val = delta, ""
            action_text = "เพิ่ม"
        else:
            new_point = current_point - delta
            point_ws.update_cell(target_row, 4, new_point)
            add_val, remove_val = "", delta
            action_text = "ลด"

        # log
        history_ws.append_row([
            "",                               
            interaction.user.display_name,
            user.mention,      
            add_val,
            remove_val,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])

        await interaction.response.send_message(
            f"✅ **{action_text}แต้มเด็กดีสำเร็จ**\n"
            f"{user.mention} ตอนนี้มี **{new_point} แต้ม** 🐶✨"
        )
