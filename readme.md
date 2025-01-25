# ✨ Usage Guide ✨

### Admins Only 
- **`/setupchannel`** - Configure the channel where reminders will be sent.
- **`/setupinterval`** - Set the intervals for reminders (e.g., x days or hours before the final due date).
- **`/export`** - Export your server's reminders and receive a backup in your DMs.

### Everyone - General Usage
- **`/add`** - Add a new reminder.
- **`/delete`** - Delete a specific reminder.
- **`/list`** - List all reminders currently set for the server.

### Starting the Bot
1. Copy the environment template file: `cp .env.ex .env`
2. Modify the environment variables in `.env` as needed.
3. Run the bot: `./manage_bot.sh`

---

# ☑️ To-Do List (TDL)

- ⚡️ **Import JSON**: Add functionality to import reminders from a JSON file.
- 📝 **Optional Description Field**: Allow assignments to have an optional description for more details.
- 📢 **Multi-Channel Support**: Enable the use of multiple channels (e.g., `dev-assignments` and `cyber-assignments`).
- ⏰ **Smart Time Defaults**: When adding reminders:
  - If no time is specified, default to `00:00:01`.
  - If only the hour is provided (e.g., `16`), auto-complete to `16:00:00`.
- ⚖️ **Command-Level Permissions**: Add the ability to control permissions for each command directly within the bot.

---

# 🎉 Full Revamp Discord Reminder Bot V2.0.0

- 🧰 **Unified File Structure**: Combined all functionalities into a single file to simplify development.
- ♻️ **Code Optimization**: Improved efficiency and readability.
- 🔁 **Slash Command Transition**: Removed prefix commands; now fully based on Discord **slash commands**.
- 🔐 **Backup Functionality**: Added `/export` command to send server-specific backups.
- ➖ **Split Settings Commands**: Divided configuration into `/setupchannel` and `/setupinterval` for better clarity.
- 🌐 **Legacy Support**: Created a new branch for the older prefix-based version.
