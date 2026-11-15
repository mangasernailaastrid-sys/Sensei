# BE A FIGHTER Discord bot

Python bot for welcome messages and permission-checked moderation. Settings persist in a local SQLite database. No Roblox account or game data integration is included.

## Run in PyCharm

1. Open this folder as a PyCharm project. Use Python 3.11 or newer and a project virtual environment.
2. Install `requirements.txt` using PyCharm's package prompt, or run `python -m pip install -r requirements.txt` in its terminal.
3. In the [Discord Developer Portal](https://discord.com/developers/applications), create an application named **BE A FIGHTER**, then open its Bot page. Copy its bot token into a local `.env` file based on `.env.example`. Keep the token private; never paste it into chat or Git.
4. On the Bot page enable **Server Members Intent** for join events. Message Content Intent is not required.
5. Enable Discord Developer Mode, right-click your server, and copy its ID into `DISCORD_GUILD_ID` in `.env`.
6. Invite your application with scopes `bot` and `applications.commands`. Grant View Channels, Send Messages, Embed Links, Read Message History, Manage Messages, Moderate Members, Kick Members, and Ban Members. Place its role above the roles it will moderate. Administrator is unnecessary.
7. Right-click `bot.py` in PyCharm and choose **Run 'bot'**. The console reports when it is online. Keep the process running; closing it takes the bot offline.
8. In your server use `/welcome_setup` to select the welcome channel, then `/welcome_test` to see a private preview.

## Commands

| Command | Permission | Purpose |
| --- | --- | --- |
| `/help` | Everyone | Command list |
| `/welcome_setup` | Manage Server | Save welcome channel |
| `/welcome_test` | Manage Server | Private welcome preview |
| `/timeout` | Moderate Members | Timeout for 1–40,320 minutes |
| `/untimeout` | Moderate Members | Remove timeout |
| `/kick` | Kick Members | Remove a server member |
| `/ban` | Ban Members | Ban a member without deleting message history |
| `/clear` | Manage Messages | Scan the latest 1–100 messages and delete eligible messages |

Moderation commands check both caller and bot permissions and role hierarchy. Timeout, untimeout, kick, and ban require a reason recorded in Discord's audit log. Clear skips pinned messages and messages 14 days or older. Responses to commands are private to the caller. Automatic welcomes mention and notify only the arriving member, display the supplied animated GIF, and show the current total server member count (including bots). Private welcome previews do not ping. Sensei uses a cyan world-system announcement style.

## Verification

## Support tickets

The support panel is automatically maintained in channel `1571512402028003408`. Its persistent **Open Ticket** button creates a private text channel with access for the creator, Sensei, **City Founder** (`1571479712453369916`), and **Community Team** (`1571479796939231283`). Discord administrators always bypass channel restrictions.

Members can have one open ticket at a time. Only members with one of the two staff roles can use **Close Ticket**, followed by **Delete Ticket** confirmation. Deletion permanently removes the channel and messages; no transcript is retained. Ticket records and the panel message ID persist in `settings.db`, and buttons are registered again on startup. Sensei needs Manage Channels, View Channels, Send Messages, Embed Links, and Read Message History. Keep only one bot process running.

To test live, use Open Ticket with an ordinary member account, verify another ordinary member cannot see it, then verify the creator cannot close it and staff can. An administrator account cannot test ordinary-member privacy.

## Verification commands

Run `python -m unittest discover -s tests -v` for offline role-guard tests. Live verification needs your own Discord bot credentials and a test server: check `/help`, configure and preview welcomes, have a test account join, confirm ordinary members cannot moderate, and test moderation with a consenting test account below the moderator and bot roles.

Reference: [discord.py interaction and permission checks](https://discordpy.readthedocs.io/en/stable/interactions/api.html).
