import json
from pathlib import Path

import discord


CONFIG_PATH = Path(__file__).with_name("channel_config.json")


def get_response_channel_id() -> int | None:
    if not CONFIG_PATH.exists():
        return None

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    channel_id = config.get("channel_id")
    return int(channel_id) if channel_id is not None else None


def set_response_channel_id(channel_id: int) -> None:
    CONFIG_PATH.write_text(
        json.dumps({"channel_id": channel_id}, indent=2),
        encoding="utf-8"
    )


def public_responses_are_routed() -> bool:
    return get_response_channel_id() is not None


async def send_interaction_response(
    interaction: discord.Interaction,
    *,
    content: str | None = None,
    embed: discord.Embed | None = None,
    ephemeral: bool = False,
    view: discord.ui.View | None = None
) -> discord.Message | None:
    if ephemeral:
        if interaction.response.is_done():
            return await interaction.followup.send(
                content=content,
                embed=embed,
                ephemeral=True,
                view=view
            )
        await interaction.response.send_message(
            content=content,
            embed=embed,
            ephemeral=True,
            view=view
        )
        return None

    channel_id = get_response_channel_id()
    if channel_id is not None and interaction.guild is not None:
        channel = interaction.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            message = (
                "ช่องตอบกลับที่ตั้งไว้ไม่พบหรือไม่ใช่ช่องข้อความ "
                "ให้ Admin ตั้งค่าใหม่ด้วย /set-channel"
            )
            if interaction.response.is_done():
                await interaction.edit_original_response(
                    content=message,
                    embed=None,
                    view=None
                )
            else:
                await interaction.response.send_message(
                    message,
                    ephemeral=True
                )
            raise RuntimeError(
                f"Configured response channel {channel_id} is missing or is not a text channel"
            )

        acknowledgement = f"ส่งคำตอบไปที่ {channel.mention}"
        if interaction.response.is_done():
            await interaction.edit_original_response(
                content=acknowledgement,
                embed=None,
                view=None
            )
        else:
            await interaction.response.send_message(
                acknowledgement,
                ephemeral=True
            )

        try:
            return await channel.send(content=content, embed=embed, view=view)
        except discord.HTTPException:
            await interaction.edit_original_response(
                content=f"ส่งคำตอบไปที่ {channel.mention} ไม่สำเร็จ",
                embed=None,
                view=None
            )
            raise

    if interaction.response.is_done():
        return await interaction.followup.send(
            content=content,
            embed=embed,
            view=view
        )

    await interaction.response.send_message(
        content=content,
        embed=embed,
        view=view
    )
    return None
