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

- ⚡️ **Import JSON** ✅:
Import reminders from a JSON file using `/import`.
- 📝 **Optional Description Field** ✅:
Assignments can include an optional description field.
- 📢 **Multi-Channel Support** ✅✅ -- Done 12/02/2025 -- ✅✅:  
Enable the use of multiple channels ( to go with multi-roles which is already in place )
- ⏰ **Smart Time Defaults** ✅:
  - If no time is specified, it defaults to `00:00:01`.
  - If only the hour is provided, the bot auto-completes to `<hour>:00:00`.
  - If only the hour and minute are provided, the bot auto-completes to `<hour>:<minute>:00`.
- ⚖️ **Command-Level Permissions** ✅:
Permissions for commands can now be configured via `/setperm`.
- ❌ MASS remove Reminders ❌ ✅:
Use `/massdelete` to remove reminders by prefix.
---

# 🎉 Full Revamp Discord Reminder Bot V2.0.0

- 🧰 **Unified File Structure**:   
Combined all functionalities into a single file to simplify development.
- ♻️ **Code Optimization**:  
Improved efficiency and readability.
- 🔁 **Slash Command Transition**:   
Removed prefix commands; now fully based on Discord **slash commands**.
- 🔐 **Backup Functionality**:    
Added `/export` command to send server-specific backups.
- ➖ **Split Settings Commands**:    
Divided configuration into `/setupchannel` and `/setupinterval` for better clarity.
- 🌐 **Legacy Support**:   
Created a new branch for the older prefix-based version.
