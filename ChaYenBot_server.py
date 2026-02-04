import discord
from discord.ext import commands
from discord import app_commands
import gspread
import os, json, base64
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import random
from keep_alive import keep_alive
from result_schedule import get_schedule_result
from time_auto_schedule import check_schedule_alerts
from Point_system import get_point_sheet, setup_point_system

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_SHEETS_JSON = os.getenv("GOOGLE_SHEETS_JSON")
SHEET_URL = os.getenv("SHEET_URL")
SERVER_ID = int(os.getenv("SERVER_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

with open("emoji.json", "r", encoding="utf-8") as f:
    emoji_map = json.load(f)

scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]
base64_json = os.getenv("GOOGLE_SHEETS_JSON_BASE64")

if base64_json is None:
    raise ValueError(
        "GOOGLE_SHEETS_JSON_BASE64 not found in environment variables!")

creds_dict = json.loads(base64.b64decode(base64_json).decode("utf-8"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(SHEET_URL)
worksheet = sheet.get_worksheet(2)

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

setup_point_system(bot)

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user.name}')
    try:
        synced = await tree.sync(guild=discord.Object(id=SERVER_ID))
        print(f"🔁 Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")
        
    # bot.loop.create_task(
    #     check_schedule_alerts(bot, worksheet, channel_id=CHANNEL_ID))


# === /gay ===
@tree.command(name="gay",
              description="วันนี้คุณโทษตาเอกแล้วหรือยัง",
              guild=discord.Object(id=SERVER_ID))
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

# === /all-schedule ===
@tree.command(name="all-schedule",
              description="ดูตารางนัดทั้งหมด",
              guild=discord.Object(id=SERVER_ID))
async def all_schedule(interaction: discord.Interaction):
    result_blocks = await get_schedule_result(user=None)

    if result_blocks:
        embed = discord.Embed(
            title="📅 ตารางนัดทั้งหมดในสัปดาห์นี้~",
            description="ชาเย็นจังสรุปนัดให้เรียบร้อยแล้วน้า~ 💖",
            color=discord.Color.orange())

        for idx, block in enumerate(result_blocks, start=1):
            embed.add_field(name=f"📝 นัดที่ {idx}",
                            value=f"{block}\n\u200b",
                            inline=False)

        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="✨ ยังไม่มีนัดเลย~!",
            description="ว่างทั้งสัปดาห์เลยค่า~ ไปเที่ยวกับชาเย็นจังมั้ย~ ☁️💙",
            color=discord.Color.green())
        await interaction.response.send_message(embed=embed)


# === /user-schedule ===
@tree.command(name="user-schedule",
              description="ดูตารางนัดของผู้ใช้",
              guild=discord.Object(id=SERVER_ID))
@app_commands.describe(user="เลือกผู้ใช้ที่ต้องการดูตาราง")
async def user_schedule(interaction: discord.Interaction, user: discord.User):
    result_blocks = await get_schedule_result(user=user)

    if result_blocks:
        embed = discord.Embed(title=f"📅 ตารางนัดของ {user.display_name}~",
                              description="ชาเย็นจังสรุปให้นะคะ~ 💖🍬",
                              color=discord.Color.orange())

        for idx, block in enumerate(result_blocks, start=1):
            embed.add_field(name=f"📝 นัดที่ {idx}",
                            value=f"{block}\n\u200b",
                            inline=False)

        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title=f"✨ {user.display_name} ยังไม่มีนัดเลย~!",
                              description="ว่างโล่งเหมือนใจชาเย็นจังเลยค่ะ~ 🩵",
                              color=discord.Color.green())
        await interaction.response.send_message(embed=embed)


# === /my-schedule ===
@tree.command(name="my-schedule",
              description="ดูตารางนัดของฉัน",
              guild=discord.Object(id=SERVER_ID))
async def my_schedule(interaction: discord.Interaction):
    user = interaction.user
    result_blocks = await get_schedule_result(user=user)
    
    if result_blocks:
        embed = discord.Embed(
            title="📅 นัดของคุณค่า~!",
            description="ชาเย็นจังสรุปตารางนัดมาให้แล้วนะคะ~ 💖",
            color=discord.Color.blue())

        for idx, block in enumerate(result_blocks, start=1):
            embed.add_field(name=f"📝 นัดที่ {idx}",
                            value=f"\n{block}\n\u200b",
                            inline=False)

        # embed.set_footer(text="ชาเย็นจัง - ขยันจำตารางแทนให้เสมอเลยค่า~! 💙")
        await interaction.response.send_message(embed=embed)

    else:
        embed = discord.Embed(
            title="🎉 ไม่มีนัดค้างอยู่เลย~!",
            description=
            "ชาเย็นจังดีใจมากๆ เลยนะคะที่ไม่มีนัดค้างอยู่~ ไปพักผ่อนกันเถอะ! 💖📅",
            color=discord.Color.green())
        # embed.set_footer(text="ชาเย็นจัง - ผู้ช่วยตารางนัดสุดคิ้วท์ 💙")
        await interaction.response.send_message(embed=embed)

TARGET_ROLES = [
    "ยศหนังหมา",
    "ยศหนังหมา Extra",
    "☢️ Super Ultimate หนังหมา"
]

ADMIN_ROLE_ID = 1234436180087668736

@tree.command(
    name="clear-doggie",
    description="เคลียร์พวกหนังหมา~!",
    guild=discord.Object(id=SERVER_ID)
)
@app_commands.checks.has_role(ADMIN_ROLE_ID)
async def clear_doggie_roles(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    role_ids = [
        1409611574104293408,  # 🔹 ยศหนังหมา
        1409611755440832622,  # 🔹 ยศหนังหมา Extra
        1409611813242540052   # 🔹 ☢️ Super Ultimate หนังหมา
    ]
    cleared_summary = []

    for role_id in role_ids:
        role = interaction.guild.get_role(role_id)
        if role and interaction.guild.me.top_role > role:
            members = list(role.members)
            count = 0
            for member in members:
                await member.remove_roles(role, reason=f"Cleared by {interaction.user}")
                count += 1
            if count:
                cleared_summary.append(f"✨ เอาบทบาท **{role.name}** ออก {count} คนแล้วจ้า~!")
            else:
                cleared_summary.append(f"🍵 บทบาท **{role.name}** ไม่มีใครถืออยู่แล้วจ้า~")
        else:
            cleared_summary.append(f"⚠️ ไม่สามารถเอา **{role.name}** ออกได้ เพราะ role สูงกว่า bot")

    await interaction.followup.send("\n".join(cleared_summary), ephemeral=True)

@clear_doggie_roles.error
async def clear_doggie_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingRole):
        await interaction.response.send_message(
            "⚠️ ต้องมียศ **admin** เท่านั้นถึงจะใช้คำสั่งนี้ได้น้า~!",
            ephemeral=True
        )
    else:
        # กันพลาด error อื่น
        await interaction.response.send_message(
            f"❌ เกิดข้อผิดพลาด: {error}",
            ephemeral=True
        )


# === /help ===
@tree.command(name="help",
              description="แสดงคำสั่งทั้งหมดของบอท",
              guild=discord.Object(id=SERVER_ID))
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 ความช่วยเหลือจากชาเย็นจัง~!",
        description="**คำสั่งทั้งหมดที่คุณสามารถใช้ได้น้า~**",
        color=discord.Color.purple())

    embed.add_field(name="🍡 ความช่วยเหลือทั่วไป",
                    value="""
            > `/help` - แสดงคำสั่งทั้งหมดของบอท
            """,
                    inline=False)
    
    embed.add_field(name="🗓️ คำสั่งตารางนัด",
                    value="""
            > `/all-schedule` - ตรวจสอบนัดทั้งหมดที่ยังไม่เสร็จ
            > `/user-schedule` - ดูตารางนัดของผู้ใช้รายบุคคล
            > `/my-schedule` - ดูตารางนัดเฉพาะของคุณเอง
            > `/clear-doggie` - ล้างบทบาทยศหนังหมาทั้งหมด (ใช้ได้เฉพาะ Admin)
            """,
                    inline=False)

    embed.add_field(name="🌈 คำสั่งอยากเทสต์ระบบก็ลองเลยค่า~!",
                    value="""
            > `/gay` - วันนี้คุณโทษตาเอกแล้วหรือยังนะ~?
            """,
                    inline=False)
    
    embed.add_field(name="🐶 คำสั่งแต้มเด็กดี",
                    value="""
            > `/goodpoint` - ปรับแต้มเด็กดี (ใช้ได้เฉพาะ Admin)
            """,
                    inline=False)

    # embed.set_footer(text="ชาเย็นจัง - ผู้ช่วยนัดหมายสุดคิ้วท์ 💙")
    await interaction.response.send_message(embed=embed)

keep_alive()
bot.run(DISCORD_TOKEN)
