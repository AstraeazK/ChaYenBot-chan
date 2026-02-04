import discord
from discord import app_commands
import gspread
import os, json, base64
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random

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

def chayen_embed(title: str, description: str, color: discord.Color):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
    )
    return embed


ADMIN_ROLE_ID = 1234436180087668736

# ---------- Slash Command ----------
def setup_point_system(bot: discord.Client):

    @bot.tree.command(
        name="goodpoint",
        description="เพิ่ม / ลด แต้มเด็กดี",
        guild=discord.Object(id=int(os.getenv("SERVER_ID")))
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
        if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message(
                "⚠️ ต้องมียศ **admin** เท่านั้นถึงจะใช้คำสั่งนี้ได้น้า~!",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        sheet = get_point_sheet()
        point_ws = sheet.worksheet("Point")
        history_ws = sheet.worksheet("History")

        users = point_ws.get("C2:C")
        target_row = None

        target_name = user.name.lower()

        for i, row in enumerate(users, start=2):
            if not row:
                continue

            sheet_name = row[0].strip().lower()

            if sheet_name.startswith("@"):
                sheet_name = sheet_name[1:]

            if sheet_name == target_name:
                target_row = i
                break

        # ❌ ไม่พบ user → สุ่มข้อความ
        if not target_row:
            not_found_msgs = [
                f"🧋❓ น้องชาเย็นหา **@{user.name}** ไม่เจอเลยอ่า~\nลองเช็กชื่อในชีทแต้มเด็กดีอีกทีน้า 🐶✨",
                f"🧋🐶 เอ๊ะ… ส่องแล้วแต่ไม่พบ **@{user.name}** ในระบบแต้มเด็กดีเลย",
                f"🧋😆 ยังไม่เจอชื่อ **@{user.name}** น้า~ หรือว่ายังไม่ได้สมัครเป็นเด็กดี?",
                f"🧋📋 แจ้งจากน้องชาเย็น!\nยังไม่มีข้อมูลของ **@{user.name}** ในชีทแต้มเด็กดีเลยอ่า~"
            ]

            embed = chayen_embed(
                title="ไม่พบข้อมูลในระบบ",
                description=random.choice(not_found_msgs),
                color=discord.Color.orange()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )
            return

        current_point = float(point_ws.cell(target_row, 4).value or 0)
        delta = 0.5

        # 🛑 ป้องกันแต้มติดลบ
        if method.value == "remove" and current_point <= 0:
            embed = discord.Embed(
                title="โอ๊ะโอ~ แต้มติดลบ! ⚠️",
                description=(
                    f"น้องชาเย็นเขินเลยอะ…\n"
                    f"**@{user.name} ไม่มีแต้มให้ลบแล้วน้า~** 🥺💦\n\n"
                    f"ไว้ทำดีเพิ่มก่อน ค่อยกลับมาลบนะจ๊ะ~ ✨"
                ),
                color=discord.Color.orange()
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text="ชาเย็นคอยเชียร์อยู่ตรงนี้ 💕")

            await interaction.followup.send(embed=embed, ephemeral=True)
            return


         # ➕ / ➖ คำนวณแต้ม
        if method.value == "add":
            new_point = current_point + delta
            add_val, remove_val = delta, ""
            user_display = user.display_name
            messages = [
                f"🧋✨ น้องชาเย็นเติมพลังความดีให้เรียบร้อย!\n{user_display} ได้รับแต้มเด็กดีเพิ่มแล้ว 🐶💖\nตอนนี้มี **{new_point} แต้ม**",
                f"🧋🐶 *ปิ๊ง!* จงทำดี!\nเพิ่มแต้มให้ {user_display} สำเร็จ ✨\nแต้มปัจจุบัน **{new_point} แต้ม**",
                f"🧋😆 ทำดีแล้วน้า~\n{user_display} ได้แต้มเด็กดีเพิ่ม!\nรวมเป็น **{new_point} แต้ม** 🐾"
            ]
        else:
            new_point = current_point - delta
            add_val, remove_val = "", delta
            user_display = user.display_name
            messages = [
                f"🧋⚠️ น้องชาเย็นขอหักแต้มเบา ๆ นะ~\n{user_display} เหลือ **{new_point} แต้ม** 🐶💦",
                f"🧋😈 หนังหมากระดิกเลย!\nลดแต้ม {user_display} แล้วน้า~\nตอนนี้เหลือ **{new_point} แต้ม**",
                f"🧋🐶 อุ๊ย ๆ ความดีหล่นหาย\n{user_display} ถูกลดแต้ม\nเหลือ **{new_point} แต้ม** น้า~"
            ]

        if method.value == "add":
            embed = chayen_embed(
                title="เพิ่มแต้มเด็กดี ✨",
                description=random.choice(messages),
                color=discord.Color.green()
            )
        else:
            embed = chayen_embed(
                title="ลดแต้มเด็กดี ⚠️",
                description=random.choice(messages),
                color=discord.Color.red()
            )
        embed.set_thumbnail(url=user.display_avatar.url)
        # 📊 update sheet
        point_ws.update_cell(target_row, 4, new_point)

        # 📝 log
        history_ws.append_row([
            "",
            interaction.user.display_name,
            f"@{user.name}",
            add_val,
            remove_val,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])

        await interaction.followup.send(embed=embed)
