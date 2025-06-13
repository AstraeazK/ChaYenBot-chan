import discord
from discord.ext import commands
from discord import app_commands
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os
import json
import base64

with open("emoji.json", "r", encoding="utf-8") as f:
    emoji_map = json.load(f)

load_dotenv()
GOOGLE_SHEETS_JSON = os.getenv("GOOGLE_SHEETS_JSON")
SHEET_URL = os.getenv("SHEET_URL")

scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

base64_json = os.getenv("GOOGLE_SHEETS_JSON_BASE64")
if base64_json is None:
    raise ValueError("GOOGLE_SHEETS_JSON_BASE64 not found in environment variables!")

creds_dict = json.loads(base64.b64decode(base64_json).decode("utf-8"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
# creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_JSON, scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(SHEET_URL)
worksheet = sheet.get_worksheet(2)

async def get_schedule_result(user=None):
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
