# Discord Homework Reminder Bot

## Overview

The Discord Homework Reminder Bot is designed to help students keep track of their homework assignments by creating events and sending reminders in a designated channel. The bot supports multiple servers and (WIP) allows for customization of reminder settings.

## Features

- **Event Creation**: Automatically creates an event when a homework assignment is added.
                    People will have to check "i'm interested" on the event to get notifications, can't force it...
- **Delete Command**: Allows users to delete both the homework assignment and the associated Discord event.
- **Multi-Server Support**: The bot's JSON formatting allows it to be used across multiple servers.
![alt text](./Images/jsonformat.png)
- **System Channel Reminders**: Sends reminders in the system channel (Right click on the serer > Server Settings > Overview > Choose the channel).

    ![alt text](./Images/systemchannel.png)

## Installation

*WIP* 

## Usage
Adding Homework
### Adding Homework
`!add <date> <heure> <titre>`
### Delete Homework
`!delete <titre>`
### List all homeworks
`!list`
### Show commands 
`!usage`

#Update 19/09/2024
Revamped the bot 
Removed all type, no need to specify anymore ( default and only one now is the old "reminder" )
The reminders will be sent when there's 14,7,3,1 and less than 1 days remaining
Each commands are now split into multiple "modules" so it's easier to create/read the code 
Changed commands to make them smaller
Bot will now add a check emoji instead of sending a message ( keeping the chat clean )
Bot will create an event when adding a homework
New delete command, will delete both the homework AND the discord event 
Changed the json formatting, which allows the use of the bot in multiple servers
The bot will send the reminders in the system channel ( server settings > overview and choose the channel )
Added gitignore file
Cleaned requirement.txt
Multiple fixes I forgot since I didnt write the readme before 

TODOLIST
Fix small bugs 
Fix ratelimit or get around it / limit the commands usage 
Add a command for settings (
    Switching reminders language from french to english
    Only allows commands to specific roles / perms 
)
Add a command to automatically set the reminder channel, instead of havign to configure a system channel in discord

