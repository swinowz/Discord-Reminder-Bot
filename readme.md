# Usage
Admins only - Initial setup
/setupchannel - configure the channel on which reminders will happen
/setupinterval - configure intervals for the reminders ( x days/hours before the final due date )

Everyone - Usage
/add
/delete
/list

# TDL
* Ability to import a JSON file.
* Addition of an (optional) "description" field for assignments, to provide additional details if needed.
* Ability to use multiple channels (e.g., useful for channels like "dev-assignments" and "cyber-assignments").
* When using the add command, if no time is provided, it defaults to 00:00:01. Similarly, if only an hour is provided (e.g., 16), it automatically completes it as 16:00:00.
* Ability to control permissions on each commands directly using commands

# Full Revamp Discord Reminder Bot V2.0.0
- Made everything into one file to make the development easier
- Optimised some code
- Removed discord prefix, the bot is now 100% on discord **slash** commands
- Added a backup command, which will export your server's (only yours) data
- Split settings into two separate commands (/setupchannel /setupinterval)
- Made a new branch to push the old "prefix" version

