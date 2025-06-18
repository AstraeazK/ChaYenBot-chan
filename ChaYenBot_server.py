import discord
from discord.ext import commands
from discord import app_commands
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os
import random
import json
from keep_alive import keep_alive
from result_schedule import get_schedule_result
from time_auto_schedule import (
    check_schedule_alerts,
    clear_alerted_events_daily,
    load_alerted_events
)

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

    load_alerted_events()
    bot.loop.create_task(check_schedule_alerts(bot, worksheet, channel_id=CHANNEL_ID))
    bot.loop.create_task(clear_alerted_events_daily())


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
        "มีใครเห็นตาเอกมั้ยคะ~? เห็นว่าหัวใจเค้าสีรุ้งแวววาวเลยล่ะ~! 💓🌈",
        "แหน่ะ~! /gay ใส่ตาเอกเหรอ~? ระบบบอกว่า... ใช่จ้าาา~! 🌈🔥 หัวใจรุ้งแตกกระจายเลย~!",
        "อุ๊บ~! ไฟล์ลับของตาเอกถูกเปิดเผยแล้ว~! Gay.exe ทำงานเรียบร้อย~ 💻🌈💥",
        "โอ้โห~! ค่าพลัง Gay พุ่งทะยานเกินกราฟไปแล้วค่า~! 📈✨ ระวังหัวใจสาวๆ (และหนุ่มๆ) สั่นไหวนะคะ~! 😳💓",
        "ตรวจสอบแล้วค่า~! ตาเอกคือสมาชิก VIP แห่งชมรมหัวใจหลากสี~! 🎉🌈💖 ขอเชิญเข้าสู่โหมดน่ารักตลอดชีพเลยค่ะ~!",
        "สายรุ้งแสบตา~! ตาเอกปล่อยออร่า Gay แบบ 200% แล้วค่า~! 💥🌈 ใครไม่ไหว ออกไปตั้งหลักก่อนนะคะ~ 😆💘"
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

        # embed.set_footer(text="ชาเย็นจัง - ไม่พลาดนัดแน่นอนค่า~! 💙")
        await interaction.response.send_message(embed=embed)

    else:
        embed = discord.Embed(
            title="✨ ไม่มีนัดที่ยังไม่เสร็จแล้วน้า~!",
            description="ตารางว่างโล่งงง~ เหมือนใจชาเย็นจังเลยค่ะ~ ☁️💙\nไปพักผ่อนกันได้เต็มที่เลยนะคะ~!",
            color=discord.Color.green()
        )
        # embed.set_footer(text="ชาเย็นจัง - ผู้ช่วยจัดการตารางตัวจริง~!")
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

        # embed.set_footer(text="ชาเย็นจัง - ขยันจำตารางแทนให้เสมอเลยค่า~! 💙")
        await interaction.response.send_message(embed=embed)

    else:
        embed = discord.Embed(
            title="🎉 ไม่มีนัดค้างอยู่เลย~!",
            description="ชาเย็นจังดีใจมากๆ เลยนะคะที่ไม่มีนัดค้างอยู่~ ไปพักผ่อนกันเถอะ! 💖📅",
            color=discord.Color.green()
        )
        # embed.set_footer(text="ชาเย็นจัง - ผู้ช่วยตารางนัดสุดคิ้วท์ 💙")
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

    # embed.set_footer(text="ชาเย็นจัง - ผู้ช่วยนัดหมายสุดคิ้วท์ 💙")
    await interaction.response.send_message(embed=embed)


keep_alive()
bot.run(DISCORD_TOKEN)