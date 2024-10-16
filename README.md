# Discord Homework Reminder Bot

## Overview

The Discord Homework Reminder Bot is designed to help students keep track of their homework assignments by creating events and sending reminders in a designated channel. The bot supports multiple servers and (WIP) allows for customization of reminder settings.

![image](https://github.com/user-attachments/assets/760ebd69-d4a3-4525-8dab-a75f60352919)



## TODO List

- **Fix Small Bugs**: Address minor issues and improve stability.
- **Rate Limit Handling**: Fix or find a workaround for rate limits; limit command usage if necessary.
- **Settings Command**: Add a command to manage settings, including:
    - Switching reminder language from French to English.
    - Restricting command usage to specific roles or permissions.

## Deleted Most of the readme until I finish it ( WIP )

## Update 16/10/2024


**NEW -- Settings Command**: The !settings includes:
- Custom Reminder Intervals: check the intervals you want to use for the reminders
- Debug Generation: Quickly generate sample homework assignments for testing.
- Delete Homework Options: Choose between deleting all homework or only debug assignments.
- Improved Reminder Logic: Fixed issues with the reminder loop to ensure reminders are sent at the correct times.
- Define the reminder channe, will use system message channel by default

**Added a restriction on the commands until the reminder intervals are set**


