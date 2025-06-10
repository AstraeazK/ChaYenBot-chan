import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
import discord
from result_schedule import get_schedule_result

ALERTED_EVENTS_FILE = "alerted_events.json"
ALERTED_EVENTS = set()

def load_alerted_events():
    global ALERTED_EVENTS
    if os.path.exists(ALERTED_EVENTS_FILE):
        with open(ALERTED_EVENTS_FILE, "r") as f:
            try:
                loaded = json.load(f)
                ALERTED_EVENTS.update(int(x) for x in loaded)
            except json.JSONDecodeError:
                ALERTED_EVENTS.clear()

def save_alerted_events():
    with open(ALERTED_EVENTS_FILE, "w") as f:
        json.dump([int(x) for x in ALERTED_EVENTS], f)

async def check_schedule_alerts(bot, worksheet, channel_id):
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            col_J = worksheet.col_values(10)[3:]
            col_K = worksheet.col_values(11)[3:]
            col_L = worksheet.col_values(12)[3:]

            now = datetime.now(timezone.utc)
            target_timestamps = []

            for i in range(min(len(col_J), len(col_K), len(col_L))):
                j_val = col_J[i].strip()
                k_val = col_K[i].strip().upper()
                l_val = col_L[i].strip().upper()

                if not j_val or k_val != "TRUE" or l_val != "FALSE":
                    continue

                if j_val.startswith("<t:") and j_val.endswith(">"):
                    try:
                        timestamp_str = j_val[3:-1].split(":")[0]
                        timestamp = int(timestamp_str)
                        event_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        time_diff = (event_time - now).total_seconds()

                        if 59 * 60 <= time_diff <= 61 * 60 and timestamp not in ALERTED_EVENTS:
                            target_timestamps.append(timestamp)

                    except Exception as e:
                        print(f"[ERROR] Failed to parse timestamp: {e}")

            if target_timestamps:
                channel = bot.get_channel(channel_id)
                result_blocks = await get_schedule_result(user=None)
                sent_blocks = set()

                for block in result_blocks:
                    lines = block.splitlines()
                    block_timestamp = None

                    # หาตัว timestamp
                    for line in lines:
                        if "<t:" in line and ":F>" in line:
                            try:
                                block_timestamp = int(line.split("<t:")[1].split(":")[0])
                                break
                            except:
                                continue

                    if block_timestamp in target_timestamps:
                        block_hash = hash(block)
                        if block_hash in sent_blocks:
                            continue

                        cleaned_lines = []
                        for i, line in enumerate(lines):
                            if i == 0 and line.strip().startswith("#"):
                                continue
                            cleaned_lines.append(line.lstrip("#").strip())

                        cleaned_text = "\n".join(cleaned_lines)

                        formatted_header = f"<t:{block_timestamp}:F> ⏰ <t:{block_timestamp}:R>"
                        final_text = f"{formatted_header}\n{cleaned_text}"

                        if channel:
                            embed = discord.Embed(
                                title="⏰ เหลืออีก 1 ชั่วโมงค่า~ อย่าลืมมาน้า~ 💖",
                                description=final_text,
                                color=discord.Color.pink()
                            )
                            # embed.set_footer(text="ชาเย็นจังเตือนด้วยความรัก 💙")
                            await channel.send(embed=embed)

                        sent_blocks.add(block_hash)

                ALERTED_EVENTS.update(target_timestamps)
                save_alerted_events()


        except Exception as e:
            print(f"[ERROR] in schedule check loop: {e}")

        await asyncio.sleep(60)

async def clear_alerted_events_daily():
    await asyncio.sleep(10)
    while True:
        now = datetime.now(timezone.utc)
        next_reset = now.replace(hour=4, minute=0, second=0, microsecond=0)
        if now >= next_reset:
            next_reset += timedelta(days=1)
        wait_time = (next_reset - now).total_seconds()
        await asyncio.sleep(wait_time)

        ALERTED_EVENTS.clear()
        save_alerted_events()
        print("🔁 Cleared ALERTED_EVENTS for new day.")
