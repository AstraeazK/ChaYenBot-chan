import discord
from discord.ext import commands
from discord import app_commands
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os
import json
import random
import datetime

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_SHEETS_JSON_CONTENT = os.getenv("GOOGLE_SHEETS_JSON_CONTENT")
SHEET_URL = os.getenv("SHEET_URL")
SERVER_ID = int(os.getenv("SERVER_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

# ✅ ใช้ keyfile_dict แทน keyfile_name
info = json.loads(GOOGLE_SHEETS_JSON_CONTENT)
creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)

client = gspread.authorize(creds)
sheet = client.open_by_url(SHEET_URL)
worksheet = sheet.get_worksheet(2)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

@bot.event

async def on_ready():
    print(f'✅ Logged in as {bot.user.name}')
    try:
        synced = await tree.sync(guild=discord.Object(id=SERVER_ID))
        print(f"🔁 Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

def extract_timestamp(time_str):
    try:
        dt = datetime.datetime.strptime(time_str.strip(), "%d/%m/%Y %H:%M")
        return int(dt.timestamp())
    except Exception:
        return 0
    
async def get_schedule_result(user: discord.User = None):
    values = worksheet.get_all_values()[3:]  # ข้าม header 3 บรรทัดแรก
    col_J = worksheet.col_values(10)[3:]     # เวลา (J)
    col_L = worksheet.col_values(12)[3:]     # Done (L)
    col_N = worksheet.col_values(14)[3:]     # Block ชื่อบอส (N)

    result_blocks = []

    for i in range(0, len(col_L), 2):
        is_done = col_L[i].strip().upper()
        block = col_N[i].strip()
        if is_done != "FALSE" or not block:
            continue

        job_row = values[i + 1] if i + 1 < len(values) else []
        name_row = values[i] if i < len(values) else []

        combined_lines = []
        for col in range(0, min(len(name_row), len(job_row)), 2):  # A,C,E,...
            name = name_row[col].strip()
            job = job_row[col].strip()
            if not name:
                continue

            show_name = f"**{name}**" if user and name.lower() == user.display_name.lower() else name
            if job:
                combined_lines.append(f"{job}: {show_name}")
            else:
                combined_lines.append(show_name)

        timestamp = extract_timestamp(col_J[i]) if i < len(col_J) else 0
        time_display = f"<t:{timestamp}:F> ⏰ <t:{timestamp}:R>" if timestamp else ""
        block_text = f"**{block}**\n{time_display}\n" + "\n".join(combined_lines)
        result_blocks.append(block_text)

    return result_blocks

# === /ping ===
@tree.command(
    name="ping",
    description="วันนี้คุณโทษตาเอกแล้วหรือยัง",
    guild=discord.Object(id=SERVER_ID)
)
async def ping(interaction: discord.Interaction):
    messages = [
        "ชาเย็นจังแอบกระซิบ~ ตาเอกหัวใจสีรุ้งน่ารักมากเลยค่า~! สมกับชื่อตาเอกเป็นเกย์เลยล่ะค่ะ 💖🌈",
        "อ๊ะ~! รู้ยังคะ~? ตาเอกจังเป็นหนุ่มสายรุ้งสุดอบอุ่นเลยน้า~! 🌈🍧",
        "ตาเอก... วันนี้ก็ยังน่ารักเหมือนเดิมเลยน้า~! 💕✨",
        "ใครยังไม่โทษตาเอกวันนี้ รีบเลยนะคะ! ไม่งั้นตาเอกจะงอนแล้วน้า~ 🥺🌈",
        "มีใครเห็นตาเอกมั้ยคะ~? เห็นว่าหัวใจเค้าสีรุ้งแวววาวเลยล่ะ~! 💓🌈"
    ]
    selected_message = random.choice(messages)
    await interaction.response.send_message(selected_message)

# === /check-schedule === 
@tree.command(name="check-schedule", description="ตรวจสอบตาราง", guild=discord.Object(id=SERVER_ID))
@app_commands.describe(schedule="เลือกว่าจะดูอะไร", user="ดูตารางของ @ผู้ใช้")
@app_commands.choices(schedule=[
    discord.app_commands.Choice(name="ตารางนัดที่ยังเหลือ", value="unfinish"),
])
async def check_schedule(
    interaction: discord.Interaction,
    schedule: discord.app_commands.Choice[str],
    user: discord.User = None
):
    result_blocks = await get_schedule_result(user=user)
    if result_blocks:
        response = "\n\n".join(result_blocks)
        await interaction.response.send_message(f"**นี่ค่า~! 💖 นัดที่ยังเหลือในสัปดาห์นี้~ อย่าลืมไปตามนัดกันน้า~! 📅🍬**\n{response}")
    else:
        await interaction.response.send_message("ไม่มีตารางนัด")


# === /my-schedule === 
@tree.command(name="my-schedule", description="ดูตารางนัดของฉัน", guild=discord.Object(id=SERVER_ID))
async def my_schedule(interaction: discord.Interaction):
    user = interaction.user
    result_blocks = await get_schedule_result(user=user)
    if result_blocks:
        response = "\n\n".join(result_blocks)
        await interaction.response.send_message(f"**นัดของคุณค่า~! 💖**\n{response}")
    else:
        await interaction.response.send_message("คุณไม่มีตารางนัดที่ยังไม่เสร็จ")

bot.run(DISCORD_TOKEN)
