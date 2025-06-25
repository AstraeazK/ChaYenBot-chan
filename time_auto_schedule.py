import asyncio
from datetime import datetime, timezone
import discord
from result_schedule import get_schedule_result

async def check_schedule_alerts(bot, worksheet, channel_id):
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            col_J = worksheet.col_values(10)[3:]
            col_K = worksheet.col_values(11)[3:]
            col_L = worksheet.col_values(12)[3:]
            col_M = worksheet.col_values(13)[3:]

            now = datetime.now(timezone.utc)
            target_entries = []

            for i in range(min(len(col_J), len(col_K), len(col_L), len(col_M))):
                row_index = i + 4

                if row_index % 2 != 0:
                    continue 

                j_val = col_J[i].strip()
                k_val = col_K[i].strip().upper()
                l_val = col_L[i].strip().upper()
                m_val = col_M[i].strip().upper() if i < len(col_M) else ""

                if not j_val or k_val != "TRUE" or l_val != "FALSE" or m_val == "TRUE":
                    continue

                if j_val.startswith("<t:") and j_val.endswith(">"):
                    try:
                        timestamp_str = j_val[3:-1].split(":")[0]
                        timestamp = int(timestamp_str)
                        event_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        time_diff = (event_time - now).total_seconds()

                        if 59 * 60 <= time_diff <= 61 * 60:
                            target_entries.append((timestamp, row_index))

                    except Exception as e:
                        print(f"[ERROR] Failed to parse timestamp: {e}")

            if target_entries:
                channel = bot.get_channel(channel_id)
                result_blocks = await get_schedule_result(user=None)
                sent_blocks = set()

                for timestamp, row_index in target_entries:
                    matched_block = next((b for b in result_blocks if f"<t:{timestamp}:" in b), None)

                    if matched_block and hash(matched_block) not in sent_blocks:
                        cleaned_lines = [
                            line.lstrip("#").strip()
                            for i, line in enumerate(matched_block.splitlines())
                            if not (i == 0 and line.strip().startswith("#"))
                        ]

                        formatted_header = f"<t:{timestamp}:F> ⏰ <t:{timestamp}:R>"
                        final_text = f"{formatted_header}\n" + "\n".join(cleaned_lines)

                        if channel:
                            embed = discord.Embed(
                                title="⏰ เหลืออีก 1 ชั่วโมงค่า~ อย่าลืมมาน้า~ 💖",
                                description=final_text,
                                color=discord.Color.pink()
                            )
                            await channel.send(embed=embed)

                        sent_blocks.add(hash(matched_block))
                        worksheet.update_cell(row_index, 13, "TRUE")

        except Exception as e:
            print(f"[ERROR] in schedule check loop: {e}")

        await asyncio.sleep(60)
