import discord
from discord import app_commands
import gspread
import os, json, base64
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random
from channel_config import (
    public_responses_are_routed,
    send_interaction_response
)

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
BARISTA_ROLE_ID = 1497890819787587725

# ---------- Slash Command ----------
def setup_point_system(bot: discord.Client):

    @bot.tree.command(
        name="goodpoint",
        description="เพิ่ม / ลด แต้มเด็กดี (ใช้ได้เฉพาะ Admin/Barista)",
        guild=discord.Object(id=int(os.getenv("SERVER_ID")))
    )
    @app_commands.describe(
        method="เลือกเพิ่มหรือลดแต้ม",
        user="คนที่ต้องการปรับแต้ม",
        rank_up_user="[ไม่บังคับ] คนที่ต้องการเพิ่มยศ"
    )
    @app_commands.choices(method=[
        app_commands.Choice(name="➕ เพิ่มแต้ม", value="add"),
        app_commands.Choice(name="➖ ลดแต้ม", value="remove")
    ])
    async def goodpoint(
        interaction: discord.Interaction,
        method: app_commands.Choice[str],
        user: discord.Member,
        rank_up_user: discord.Member = None
    ):
        allowed_role_ids = {ADMIN_ROLE_ID, BARISTA_ROLE_ID}
        if not any(role.id in allowed_role_ids for role in interaction.user.roles):
            await interaction.response.send_message(
                "⚠️ ต้องมียศ **Admin หรือ Barista** เท่านั้นถึงจะใช้คำสั่งนี้ได้น้า~!",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=public_responses_are_routed()
        )

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
            user_display = user.display_name
            embed = discord.Embed(
                title="โอ๊ะโอ~ แต้มติดลบ! ⚠️",
                description=(
                    f"น้องชาเย็นเขินเลยอะ…\n"
                    f"**{user_display} ไม่มีแต้มให้ลบแล้วน้า~** 🥺💦\n\n"
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
            interaction.user.name,
            f"@{user.name}",
            add_val,
            remove_val,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])

        await send_interaction_response(interaction, embed=embed)

        # 🎖️ ถ้ามี rank_up_user ให้เพิ่มยศ
        if rank_up_user:
            DOG_ROLE_NAMES = [
                "ยศหนังหมา",
                "ยศหนังหมา Extra",
                "☢️ Super Ultimate หนังหมา",
                "ภัยพิบัติเคลื่อนที่"
            ]
            
            # หายศปัจจุบันของ rank_up_user
            dog_roles = [r for r in rank_up_user.roles if r.id in DOG_ROLE_IDS]
            
            if dog_roles:
                # มียศแล้ว หาตำแหน่งในลิสต์
                current_role = max(dog_roles, key=lambda r: DOG_ROLE_IDS.index(r.id))
                current_index = DOG_ROLE_IDS.index(current_role.id)
                
                # ถ้าอยู่ยศสุดท้าย (ภัยพิบัติเคลื่อนที่) ไม่ต้องเปลี่ยน
                if current_index == len(DOG_ROLE_IDS) - 1:
                    await send_interaction_response(
                        interaction,
                        content=(
                            f"⚠️ **{rank_up_user.display_name}** อยู่ยศสูงสุดแล้ว "
                            f"({DOG_ROLE_NAMES[current_index]}) ไม่สามารถเพิ่มได้เลยน้า~"
                        ),
                        ephemeral=True
                    )
                else:
                    # เพิ่มยศขึ้นหนึ่งขั้น
                    old_role_id = DOG_ROLE_IDS[current_index]
                    new_role_id = DOG_ROLE_IDS[current_index + 1]
                    
                    old_role = interaction.guild.get_role(old_role_id)
                    new_role = interaction.guild.get_role(new_role_id)
                    
                    if old_role and new_role:
                        await rank_up_user.remove_roles(old_role)
                        await rank_up_user.add_roles(new_role)
                        
                        rank_embed = discord.Embed(
                            title=f"🎉 เพิ่มยศให้ {rank_up_user.display_name} สำเร็จ!",
                            description=(
                                f"**ยศเก่า:** {DOG_ROLE_NAMES[current_index]}\n"
                                f"**ยศใหม่:** {DOG_ROLE_NAMES[current_index + 1]}\n\n"
                                f"น้องชาเย็นเชียร์ให้นะคะ~ ✨💖"
                            ),
                            color=discord.Color.gold()
                        )
                        rank_embed.set_thumbnail(url=rank_up_user.display_avatar.url)
                        await send_interaction_response(interaction, embed=rank_embed)
            else:
                # ไม่มียศเลย เพิ่มยศแรก
                first_role_id = DOG_ROLE_IDS[0]
                first_role = interaction.guild.get_role(first_role_id)
                
                if first_role:
                    await rank_up_user.add_roles(first_role)
                    
                    rank_embed = discord.Embed(
                        title=f"🎉 เพิ่มยศให้ {rank_up_user.display_name} สำเร็จ!",
                        description=(
                            f"**ยศใหม่:** {DOG_ROLE_NAMES[0]} 🎖️\n\n"
                            f"ยินดีต้อนรับเข้าสู่อันดับหนังหมาค่ะ~ 🐕💖"
                        ),
                        color=discord.Color.gold()
                    )
                    rank_embed.set_thumbnail(url=rank_up_user.display_avatar.url)
                    await send_interaction_response(interaction, embed=rank_embed)
 
    @bot.tree.command(
            
        name="mypoint",
        description="ดูแต้มเด็กดีของตัวเอง 🐶✨",
        guild=discord.Object(id=int(os.getenv("SERVER_ID")))
    )

    async def mypoint(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        sheet = get_point_sheet()
        point_ws = sheet.worksheet("Point")

        users = point_ws.get("C2:C")
        target_row = None

        target_name = interaction.user.name.lower()

        for i, row in enumerate(users, start=2):
            if not row:
                continue

            sheet_name = row[0].strip().lower()
            if sheet_name.startswith("@"):
                sheet_name = sheet_name[1:]

            if sheet_name == target_name:
                target_row = i
                break

        # ---------- ไม่พบ user ----------
        if not target_row:
            not_found_msgs = [
                "น้องชาเย็นเปิดสมุดแต้มแล้ว… แต่ยังไม่เจอชื่อคุณเลย",
                "หรือยังไม่เคยได้รับแต้มเด็กดีกันนะ?"
            ]

            embed = discord.Embed(
                title="ไม่พบแต้มเด็กดี",
                description=random.choice(not_found_msgs),
                color=0xF5A623
            )
            embed.set_footer(text="ลองทำดีดูอีกนิด แล้วกลับมาดูใหม่น้า~ 💖")

            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # ---------- พบ user ----------
        point = float(point_ws.cell(target_row, 4).value or 0)

        success_msgs = [
            "น้องชาเย็นเช็กสมุดแต้มให้แล้ว!",
            "🐶📒 เปิดสมุดแต้มเด็กดีให้ดู~",
            "มาดูผลงานความดีของคุณกัน!"
        ]

        embed = discord.Embed(
            title="แต้มเด็กดีของคุณ 🐾",
            description=random.choice(success_msgs),
            color=0x9BE7C4
        )
        embed.add_field(
            name="ชื่อในเซิร์ฟเวอร์",
            value=interaction.user.display_name,
            inline=False
        )
        embed.add_field(
            name="แต้มเด็กดีทั้งหมด",
            value=f"**{point} แต้ม** 🧋",
            inline=False
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    DOG_ROLE_IDS = [
        1409611574104293408,  # ยศหนังหมา
        1409611755440832622,  # ยศหนังหมา Extra
        1409611813242540052,  # Super Ultimate หนังหมา
        1442895665301557450,  # ภัยพิบัติเคลื่อนที่
        1468581950527766561   # ตีพ่อตีแม่
    ]   

    class ConfirmUsePoint(discord.ui.View):
        def __init__(self, author, target, role_to_remove, role_to_add, row, current_point):
            super().__init__(timeout=30)
            self.author = author
            self.target = target
            self.role_to_remove = role_to_remove
            self.role_to_add = role_to_add
            self.row = row
            self.current_point = current_point
            self.message: discord.Message | None = None

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user != self.author:
                await interaction.response.send_message(
                    "ปุ่มนี้ไม่ใช่ของคุณน้า~",
                    ephemeral=True
                )
                return False
            return True

        @discord.ui.button(label="ยืนยัน 💖", style=discord.ButtonStyle.success)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):

            # ---------- ใช้แต้ม ----------
            sheet = get_point_sheet()
            point_ws = sheet.worksheet("Point")
            history_ws = sheet.worksheet("History")

            new_point = max(0, self.current_point - 1)
            point_ws.update_cell(self.row, 4, new_point)

            await self.target.remove_roles(self.role_to_remove)
            if self.role_to_add:
                await self.target.add_roles(self.role_to_add)

            history_ws.append_row([
                "",
                interaction.user.display_name,
                f"@{interaction.user.name}",
                "",
                1,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])

            if self.message:
                await self.message.edit(
                    embed=discord.Embed(
                        title="ดำเนินการเรียบร้อย",
                        description="น้องชาเย็นจัดการให้แล้วน้า~",
                        color=0xB0B0B0
                    ),
                    view=None
                )

            embed = discord.Embed(
                title=f"ลดยศหนังหมาให้ {self.target.display_name} สำเร็จ 🎉",
                description=(
                    f"✨ ความดีครั้งนี้มาจาก\n"
                    f"💖 **{interaction.user.display_name}**\n\n"
                    f"📒 แต้มเด็กดีคงเหลือ\n"
                    f"**{new_point} แต้ม**"
                ),
                color=0x9BE7C4
            )

            embed.set_thumbnail(url=self.target.display_avatar.url)

            await send_interaction_response(interaction, embed=embed)
            self.stop()

        @discord.ui.button(label="ยกเลิก ❌", style=discord.ButtonStyle.danger)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.message:
                await self.message.edit(
                    embed=discord.Embed(
                        title="ยกเลิกการใช้แต้ม",
                        description=(
                            "โอเคเลยน้า~ 💭\n"
                            "น้องชาเย็นยังไม่ได้ใช้แต้มให้ใครเลย\n\n"
                            "คิดอีกครั้งแล้วค่อยมากดใหม่ได้เสมอ 🐶✨"
                        ),
                        color=0xB0B0B0
                    ),
                    view=None
                )
            self.stop()

    @bot.tree.command(
        name="usepoint",
        description="ใช้แต้มเด็กดีเพื่อลดยศหนังหมา 🐶⬇️",
        guild=discord.Object(id=int(os.getenv("SERVER_ID")))
    )
    @app_commands.describe(
        user="คนที่ต้องการลดยศ (ตัวเองหรือผู้อื่น)"
    )
    async def usepoint(interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        dog_roles = [r for r in user.roles if r.id in DOG_ROLE_IDS]
        if not dog_roles:
            await interaction.followup.send(
                f"🧋😇 **{user.display_name}** ไม่มีหนังหมาให้ลดยศเลยน้า~",
                ephemeral=True
            )
            return

        current_role = max(dog_roles, key=lambda r: DOG_ROLE_IDS.index(r.id))
        current_index = DOG_ROLE_IDS.index(current_role.id)

        role_to_remove = current_role
        role_to_add = None
        if current_index > 0:
            role_to_add = interaction.guild.get_role(DOG_ROLE_IDS[current_index - 1])

        sheet = get_point_sheet()
        point_ws = sheet.worksheet("Point")

        users = point_ws.get("C2:C")
        caller_row = None
        caller_name = interaction.user.name.lower()

        for i, row in enumerate(users, start=2):
            if row and row[0].lstrip("@").lower() == caller_name:
                caller_row = i
                break

        if not caller_row:
            await interaction.followup.send(
                "น้องชาเย็นหาแต้มของคุณไม่เจอเลย",
                ephemeral=True
            )
            return

        current_point = float(point_ws.cell(caller_row, 4).value or 0)
        if current_point < 1:
            await interaction.followup.send(
                "แต้มไม่พอเลยน้า~ ทำดีเพิ่มอีกนิดก่อน!",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="ยืนยันการใช้แต้ม",
            description=(
                f"ใช้ **1 แต้มเด็กดี**\n"
                f"เพื่อลดยศหนังหมาให้ **{user.display_name}** ใช่ไหม?"
            ),
            color=0xF5A623
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        view = ConfirmUsePoint(
            author=interaction.user,
            target=user,
            role_to_remove=role_to_remove,
            role_to_add=role_to_add,
            row=caller_row,
            current_point=current_point
        )

        msg = await interaction.followup.send(
            embed=embed,
            view=view,
            ephemeral=True
        )
        view.message = msg

    @bot.tree.command(
    name="ranking",
    description="ดูอันดับเด็กดีประจำเซิร์ฟเวอร์ 🏆🐶",
    guild=discord.Object(id=int(os.getenv("SERVER_ID")))
    )
    async def ranking(interaction: discord.Interaction):
        await interaction.response.defer(
            ephemeral=public_responses_are_routed()
        )

        sheet = get_point_sheet()
        point_ws = sheet.worksheet("Point")

        rows = point_ws.get("C2:D")

        data = []
        for username, point in rows:
            try:
                point_val = float(point)
            except:
                point_val = 0.0

            if point_val <= 0:
                continue

            clean_name = username.lstrip("@")
            member = discord.utils.find(
                lambda m: m.name.lower() == clean_name.lower(),
                interaction.guild.members
            )

            display_name = member.display_name if member else clean_name
            data.append({
                "name": display_name,
                "user": member,
                "point": point_val
            })

        if not data:
            await send_interaction_response(
                interaction,
                content="ตอนนี้ยังไม่มีใครมีแต้มเด็กดีเลยน้า~"
            )
            return

        data.sort(key=lambda x: x["point"], reverse=True)

        ranked = []
        current_rank = 0
        last_point = None

        for item in data:
            if last_point is None or item["point"] < last_point:
                current_rank += 1
            last_point = item["point"]

            if current_rank > 5:
                break

            ranked.append({
                **item,
                "rank": current_rank
            })

        rank_emoji = {
            1: "🥇",
            2: "🥈",
            3: "🥉",
            4: "4️⃣",
            5: "5️⃣"
        }

        lines = []
        for r in ranked:
            emoji = rank_emoji.get(r["rank"], "")
            lines.append(
                f"{emoji} {r['name']} — {r['point']} แต้ม 🧋"
            )

        embed = discord.Embed(
            title="🏆 อันดับเด็กดีประจำเซิร์ฟเวอร์ 🐶✨",
            description="\n".join(lines) + "\n\nทุกความดี น้องชาเย็นเห็นนะ 💖",
            color=0x9BE7C4
        )

        await send_interaction_response(interaction, embed=embed)
