import discord
from discord.ext import commands
from discord import app_commands
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os
import random
import json

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_SHEETS_JSON = os.getenv("GOOGLE_SHEETS_JSON")
SHEET_URL = os.getenv("SHEET_URL")
SERVER_ID = int(os.getenv("SERVER_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

with open("emoji.json", "r", encoding="utf-8") as f:
    emoji_map = json.load(f)

scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_JSON, scope)
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

async def get_schedule_result(user: discord.User = None):
    col_K = worksheet.col_values(11)[3:]
    col_L = worksheet.col_values(12)[3:]
    col_N = worksheet.col_values(14)[3:]

    result_blocks = []

    for i in range(0, len(col_L), 2):
        if i >= len(col_K):
            continue

        k_value = col_K[i].strip().upper()
        if k_value != "TRUE":
            continue

        is_done = col_L[i].strip().upper()
        block = col_N[i].strip()

        if is_done == "FALSE" and block:
            if user:
                username = f"@{user.name.lower()}"
                if username not in block.lower():
                    continue

                block_lines = block.splitlines()
                updated_lines = []
                for line in block_lines:
                    if username in line.lower():
                        before_at, after_at = line.split("@", 1)
                        if ":" in before_at:
                            icon, name = before_at.rsplit(":", 1)
                            name = name.strip()
                            icon = icon.strip()
                            line = f"{icon}: **{name}**"
                        else:
                            name = before_at.strip()
                            line = f"**{name}**"
                    elif "@" in line:
                        line = line.split("@")[0].strip()
                    updated_lines.append(line)
                block = "\n".join(updated_lines)
            else:
                block_lines = block.splitlines()
                block = "\n".join(line.split("@")[0].strip() if "@" in line else line for line in block_lines)

            for key, emoji in emoji_map.items():
                block = block.replace(f":{key}:", emoji)

            result_blocks.append(block)


    return result_blocks



# === /gay ===
@tree.command(
    name="gay",
    description="วันนี้คุณโทษตาเอกแล้วหรือยัง",
    guild=discord.Object(id=SERVER_ID)
)
async def ping(interaction: discord.Interaction):
    messages = [
        "ชาเย็นจังแอบกระซิบ~ ตาเอกหัวใจสีรุ้งน่ารักมากเลยค่า~! สมกับชื่อตาเอกเป็นเกย์เลยล่ะค่ะ 💖🌈",
        "อ๊ะ~! รู้ยังคะ~? ตาเอกจังเป็นหนุ่มสายรุ้งสุดจะเกย์เลยน้า~! 🌈🍧",
        "ตาเอก... วันนี้ก็ยังเกย์เหมือนเดิมเลยน้า~! 💕✨",
        "ใครยังไม่โทษตาเอกวันนี้ รีบเลยนะคะ! ไม่งั้นตาเอกจะเกย์ใส่แล้วน้า~ 🥺🌈",
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
        embed = discord.Embed(
            title="📅 นัดที่ยังเหลือในสัปดาห์นี้~",
            description="อย่าลืมไปตามนัดกันน้า~ ชาเย็นจังเป็นห่วงนะคะ~! 💖🍬",
            color=discord.Color.orange()
        )

        for idx, block in enumerate(result_blocks, start=1):
            embed.add_field(
                name=f"📝 นัดที่ {idx}",
                value=f"\n{block}\n\u200b",
                inline=False
            )

        embed.set_footer(text="ชาเย็นจัง - ไม่พลาดนัดแน่นอนค่า~! 💙")
        await interaction.response.send_message(embed=embed)

    else:
        embed = discord.Embed(
            title="✨ ไม่มีนัดที่ยังไม่เสร็จแล้วน้า~!",
            description="ตารางว่างโล่งงง~ เหมือนใจชาเย็นจังเลยค่ะ~ ☁️💙\nไปพักผ่อนกันได้เต็มที่เลยนะคะ~!",
            color=discord.Color.green()
        )
        embed.set_footer(text="ชาเย็นจัง - ผู้ช่วยจัดการตารางตัวจริง~!")
        await interaction.response.send_message(embed=embed)


# === /my-schedule === 
@tree.command(name="my-schedule", description="ดูตารางนัดของฉัน", guild=discord.Object(id=SERVER_ID))
async def my_schedule(interaction: discord.Interaction):
    user = interaction.user
    result_blocks = await get_schedule_result(user=user)

    if result_blocks:
        embed = discord.Embed(
            title="📅 นัดของคุณค่า~!",
            description="ชาเย็นจังสรุปตารางนัดมาให้แล้วนะคะ~ 💖",
            color=discord.Color.blue()
        )

        for idx, block in enumerate(result_blocks, start=1):
            embed.add_field(
                name=f"📝 นัดที่ {idx}",
                value=f"\n{block}\n\u200b",
                inline=False
            )

        embed.set_footer(text="ชาเย็นจัง - ขยันจำตารางแทนให้เสมอเลยค่า~! 💙")
        await interaction.response.send_message(embed=embed)

    else:
        embed = discord.Embed(
            title="🎉 ไม่มีนัดค้างอยู่เลย~!",
            description="ชาเย็นจังดีใจมากๆ เลยนะคะที่ไม่มีนัดค้างอยู่~ ไปพักผ่อนกันเถอะ! 💖📅",
            color=discord.Color.green()
        )
        embed.set_footer(text="ชาเย็นจัง - ผู้ช่วยตารางนัดสุดคิ้วท์ 💙")
        await interaction.response.send_message(embed=embed)


# === /help === 
@tree.command(name="help", description="แสดงคำสั่งทั้งหมดของบอท", guild=discord.Object(id=SERVER_ID))
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 ความช่วยเหลือจากชาเย็นจัง~!",
        description="**คำสั่งทั้งหมดที่คุณสามารถใช้ได้น้า~**",
        color=discord.Color.purple()
    )

    embed.add_field(
        name="🗓️ คำสั่งตารางนัด",
        value="""
            > `/check-schedule` - ตรวจสอบนัดทั้งหมดที่ยังไม่เสร็จ!  
            > `/my-schedule` - ดูตารางนัดเฉพาะของคุณเอง!
            """,
        inline=False
    )

    embed.add_field(
        name="🌈 คำสั่งอยากเทสต์ระบบก็ลองเลยค่า~!",
        value="""
            > `/gay` - วันนี้คุณโทษตาเอกแล้วหรือยังนะ~?
            """,
        inline=False
    )

    embed.set_footer(text="ชาเย็นจัง - ผู้ช่วยนัดหมายสุดคิ้วท์ 💙")
    await interaction.response.send_message(embed=embed)



bot.run(DISCORD_TOKEN)