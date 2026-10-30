# 🍵 ChaYenBot-chan

A cute and helpful Discord bot designed to make server management easier! 🐾

ChaYenBot-chan provides schedule viewing, a point reward system, role management, and useful admin tools — all integrated with Google Sheets.

## ✨ Features

### 📅 Schedule System
- `/all-schedule` — View all pending schedules.
- `/user-schedule` — View schedules for a specific user.
- `/my-schedule` — View your own schedules.

### ⭐ Point System
- `/goodpoint` — Add or remove points from a user. (Admin / Barista)
- `/mypoint` — Check your current points.
- `/usepoint` — Spend points to reduce a Doggie role.
- `/ranking` — View the point leaderboard.

### 🐶 Role Management
- `/clear-doggie` — Remove Doggie roles from a user. (Admin / Barista)
- Automatically clears Doggie roles every Wednesday at 14:00 (Asia/Bangkok).

### ⚙️ Server Management
- `/set-channel` — Set the channel for public command responses. (Admin)
- `/help` — View available commands and usage information.
- `/gay` — A random fun command!

## 📋 Requirements

- Python 3.10+
- Discord Bot Application
- Google Cloud Service Account with Google Sheets API enabled
- Google Sheets for schedule, emoji, and point data

## 🚀 Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/AstraeazK/ChaYenBot-chan.git
   cd ChaYenBot-chan
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure your environment variables.

   Create a `.env` file in the project root:

   ```env
   DISCORD_TOKEN=your_discord_bot_token
   SERVER_ID=your_discord_server_id

   SHEET_URL=your_schedule_google_sheet_url
   Emoji_SHEET_URL=your_emoji_google_sheet_url
   POINT_SHEET_URL=your_point_google_sheet_url

   GOOGLE_SHEETS_JSON_BASE64=your_base64_encoded_service_account_json
   ```

4. Enable the required Discord Gateway Intents:
   - Server Members Intent

5. Invite the bot to your Discord server with the necessary permissions.

6. Start the bot:

   ```bash
   python ChaYenBot_server.py
   ```

## 🔐 Permissions

The bot uses Discord role-based permissions:

| Role | Permissions |
|---|---|
| Admin | Configure response channel, manage Doggie roles, and manage points |
| Barista | Clear Doggie roles and manage points |
| Members | Use general commands and personal point commands |

The Admin role ID and Barista role ID are configured in the source code.

## 📊 Google Sheets Integration

ChaYenBot-chan uses Google Sheets to store and retrieve information.

The point system uses two worksheets:

- `Point` — Stores user point balances.
- `History` — Records point transactions.

Make sure the Google Service Account has access to the relevant spreadsheets.

## 📝 Notes

- Public command responses can be routed to a configured channel using `/set-channel`.
- Ephemeral responses remain visible only to the user who invoked the command.
- Weekly Doggie role cleanup runs on Wednesday at 14:00 (Asia/Bangkok).
- The schedule system currently supports viewing schedules; automatic schedule notifications are not included in the current version.

## 💖 Credits

Made with love for our Discord community.

**ChaYenBot-chan** — Your little server companion! 🐾🍵
