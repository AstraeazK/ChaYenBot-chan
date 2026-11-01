import base64
import json
import logging
import os
import random
from datetime import datetime, time
from zoneinfo import ZoneInfo

import discord
import gspread
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

from channel_config import (
    send_interaction_response,
    set_response_channel_id
)
from result_schedule import get_schedule_result
from Point_system import setup_point_system


ADMIN_ROLE_ID = 1234436180087668736
Barista_ROLE_ID = 1497890819787587725
DOGGIE_ROLE_IDS = [
    1409611574104293408,
    1409611755440832622,
    1409611813242540052,
    1442895665301557450
]
DOGGIE_RESET_ANNOUNCEMENT_CHANNEL_ID = 1418965592450273422
THAILAND_TZ = ZoneInfo("Asia/Bangkok")
logger = logging.getLogger(__name__)

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SHEET_URL = os.getenv("SHEET_URL")
EMOJI_SHEET_URL = os.getenv("Emoji_SHEET_URL")
SERVER_ID = int(os.getenv("SERVER_ID"))

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

def load_emoji_map():
    try:
        emoji_sheet = client.open_by_url(EMOJI_SHEET_URL)
        emoji_worksheet = emoji_sheet.sheet1
        col_C = emoji_worksheet.col_values(3)[1:]
        col_D = emoji_worksheet.col_values(4)[1:]
        
        emoji_map = {}
        for name, emoji in zip(col_C, col_D):
            if name and emoji:
                emoji_map[name.strip()] = emoji.strip()
        
        print(f"✅ Loaded {len(emoji_map)} emojis from Google Sheets")
        return emoji_map
    except Exception as e:
        print(f"❌ Failed to load emoji map from Google Sheets: {e}")
        print("Falling back to emoji.json...")
        try:
            with open("emoji.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e2:
            print(f"❌ Failed to load emoji.json: {e2}")
            return {}

emoji_map = load_emoji_map()

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
    if not clear_doggie_roles_weekly.is_running():
        clear_doggie_roles_weekly.start()


async def clear_doggie_guild_roles(guild: discord.Guild, reason: str) -> list[str]:
    cleared_summary: list[str] = []
    bot_member = guild.me

    for role_id in DOGGIE_ROLE_IDS:
        role = guild.get_role(role_id)

        if role and bot_member and bot_member.top_role > role:
            members = list(role.members)
            for member in members:
                await member.remove_roles(role, reason=reason)

            if members:
                cleared_summary.append(
                    f"✨ เอาบทบาท **{role.name}** ออก {len(members)} คนแล้วจ้า~!"
                )
            else:
                cleared_summary.append(
                    f"🍵 บทบาท **{role.name}** ไม่มีใครถืออยู่แล้วจ้า~"
                )
        elif role:
            cleared_summary.append(
                f"⚠️ ไม่สามารถเอา **{role.name}** ออกได้ เพราะ role สูงกว่า bot"
            )
        else:
            cleared_summary.append(f"⚠️ ไม่พบ role ID: {role_id}")

    return cleared_summary

# ==================================== ล้างยศอัตโนมัติทุกวันพุธเวลา 15:00 น. ไทย ====================================
@tasks.loop(time=time(hour=15, minute=0, tzinfo=THAILAND_TZ))
async def clear_doggie_roles_weekly():
    if datetime.now(THAILAND_TZ).weekday() != 2:
        return

    guild = bot.get_guild(SERVER_ID)
    if guild is None:
        logger.error("Could not find guild %s for the weekly doggie role reset", SERVER_ID)
        return

    try:
        summary = await clear_doggie_guild_roles(
            guild,
            reason="Weekly Wednesday doggie role reset"
        )
        logger.info("Weekly doggie role reset: %s", " | ".join(summary))
    except Exception:
        logger.exception("Failed to complete the weekly doggie role reset")
        return

    channel = bot.get_channel(DOGGIE_RESET_ANNOUNCEMENT_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(DOGGIE_RESET_ANNOUNCEMENT_CHANNEL_ID)
        except discord.HTTPException:
            logger.exception("Failed to fetch the doggie reset announcement channel")
            return

    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        logger.error(
            "Doggie reset announcement channel %s is not a text channel",
            DOGGIE_RESET_ANNOUNCEMENT_CHANNEL_ID
        )
        return

    announcement = discord.Embed(
        description=(
            "🍧 ปุ๊งปั๊ง~! ถึงเวลารีเซ็ตยศหนังหมาประจำสัปดาห์แล้วค่าา~!\n"
            "ใครจะได้เลื่อนขั้น ใครจะได้อยู่ต่อ... ขอให้โชคดีนะคะ อิอิ~ 🐶💖"
        ),
        color=discord.Color(0xFF0066)
    )
    try:
        await channel.send(embed=announcement)
        logger.info(
            "Sent weekly doggie role reset announcement to channel %s",
            DOGGIE_RESET_ANNOUNCEMENT_CHANNEL_ID
        )
    except discord.HTTPException:
        logger.exception("Failed to send the doggie reset announcement")


@clear_doggie_roles_weekly.before_loop
async def before_clear_doggie_roles_weekly():
    await bot.wait_until_ready()


# ==================================== /gay ====================================
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
    await send_interaction_response(interaction, content=selected_message)

# ==================================== /all-schedule =======================================
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

        await send_interaction_response(interaction, embed=embed)
    else:
        embed = discord.Embed(
            title="✨ ยังไม่มีนัดเลย~!",
            description="ว่างทั้งสัปดาห์เลยค่า~ ไปเที่ยวกับชาเย็นจังมั้ย~ ☁️💙",
            color=discord.Color.green())
        await send_interaction_response(interaction, embed=embed)


# ==================================== /user-schedule ====================================
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

        await send_interaction_response(interaction, embed=embed)
    else:
        embed = discord.Embed(title=f"✨ {user.display_name} ยังไม่มีนัดเลย~!",
                              description="ว่างโล่งเหมือนใจชาเย็นจังเลยค่ะ~ 🩵",
                              color=discord.Color.green())
        await send_interaction_response(interaction, embed=embed)


# ==================================== /my-schedule ====================================
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
        await send_interaction_response(interaction, embed=embed)

    else:
        embed = discord.Embed(
            title="🎉 ไม่มีนัดค้างอยู่เลย~!",
            description=
            "ชาเย็นจังดีใจมากๆ เลยนะคะที่ไม่มีนัดค้างอยู่~ ไปพักผ่อนกันเถอะ! 💖📅",
            color=discord.Color.green())
        # embed.set_footer(text="ชาเย็นจัง - ผู้ช่วยตารางนัดสุดคิ้วท์ 💙")
        await send_interaction_response(interaction, embed=embed)

# ==================================== /clear-doggie ====================================
@tree.command(
    name="clear-doggie",
    description="เคลียร์พวกหนังหมา~! (ใช้ได้เฉพาะ Admin/Barista)",
    guild=discord.Object(id=SERVER_ID)
)
@app_commands.checks.has_any_role(ADMIN_ROLE_ID, Barista_ROLE_ID)
async def clear_doggie_roles(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if interaction.guild is None:
        await interaction.followup.send(
            "คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์",
            ephemeral=True
        )
        return

    cleared_summary = await clear_doggie_guild_roles(
        interaction.guild,
        reason=f"Cleared by {interaction.user}"
    )
    await send_interaction_response(
        interaction,
        content="\n".join(cleared_summary),
        ephemeral=True
    )

# ==================================== /set-channel ====================================
@tree.command(
    name="set-channel",
    description="ตั้งช่องสำหรับคำตอบสาธารณะของบอท (Admin)",
    guild=discord.Object(id=SERVER_ID)
)
@app_commands.checks.has_role(ADMIN_ROLE_ID)
@app_commands.describe(channel="ช่องที่จะให้บอทส่งคำตอบสาธารณะ")
async def set_channel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    bot_member = interaction.guild.me if interaction.guild else None
    if bot_member is None or not channel.permissions_for(bot_member).send_messages:
        await interaction.response.send_message(
            "บอทไม่มีสิทธิ์ส่งข้อความในช่องนี้",
            ephemeral=True
        )
        return

    set_response_channel_id(channel.id)
    await interaction.response.send_message(
        f"ตั้งช่องตอบกลับของบอทเป็น {channel.mention} แล้ว",
        ephemeral=True
    )


@set_channel.error
async def set_channel_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.MissingRole):
        message = "⚠️ ต้องมียศ **Admin** เท่านั้นถึงจะตั้งช่องตอบกลับได้"
    else:
        message = f"❌ ตั้งช่องตอบกลับไม่สำเร็จ: {error}"

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)

@clear_doggie_roles.error
async def clear_doggie_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingAnyRole):
        await interaction.response.send_message(
            "⚠️ ต้องมียศ **Admin หรือ Barista** เท่านั้นถึงจะใช้คำสั่งนี้ได้น้า~!",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ เกิดข้อผิดพลาด: {error}",
            ephemeral=True
        )


# ==================================== /help ====================================
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
            > `/set-channel` - ตั้งช่องรับคำตอบสาธารณะของบอท (Admin)
            """,
                    inline=False)
    
    embed.add_field(name="🗓️ คำสั่งตารางนัด",
                    value="""
            > `/all-schedule` - ตรวจสอบนัดทั้งหมดที่ยังไม่เสร็จ
            > `/user-schedule` - ดูตารางนัดของผู้ใช้รายบุคคล
            > `/my-schedule` - ดูตารางนัดเฉพาะของคุณเอง
            > `/clear-doggie` - ล้างบทบาทยศหนังหมา (Admin/Barista)
            > ระบบล้างยศหนังหมาอัตโนมัติทุกวันพุธ เวลา 13:00 น. ไทย
            """,
                    inline=False)

    embed.add_field(name="🌈 คำสั่งอยากเทสต์ระบบก็ลองเลยค่า~!",
                    value="""
            > `/gay` - วันนี้คุณโทษตาเอกแล้วหรือยังนะ~?
            """,
                    inline=False)
    
    embed.add_field(name="🐶 คำสั่งแต้มเด็กดี",
                    value="""
            > `/goodpoint` - ปรับแต้มเด็กดี (Admin/Barista)
            > `/mypoint` - ดูแต้มเด็กดีของตัวเอง
            > `/usepoint` - ใช้แต้มเด็กดีเพื่อลดยศหนังหมา
            > `/ranking` - ดูอันดับแต้มเด็กดีประจำเซิร์ฟเวอร์
            """,
                    inline=False)

    # embed.set_footer(text="ชาเย็นจัง - ผู้ช่วยนัดหมายสุดคิ้วท์ 💙")
    await send_interaction_response(interaction, embed=embed)

bot.run(DISCORD_TOKEN)
