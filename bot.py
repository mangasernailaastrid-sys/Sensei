"""BE A FIGHTER community bot. Run this file in PyCharm."""
import logging
import os
import sqlite3
from datetime import timedelta
from pathlib import Path

import discord
from discord import app_commands
from dotenv import load_dotenv
from tickets import OpenTicket, CloseTicket, ensure_panel

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
log = logging.getLogger('fighter')
WELCOME_GIF = 'https://media.giphy.com/media/JFys5DN3aRmY3Iy5yL/giphy.gif'


def setting(guild_id: int, channel_id: int | None = None) -> int | None:
    with sqlite3.connect(ROOT / 'settings.db') as db:
        db.execute('CREATE TABLE IF NOT EXISTS welcome (guild INTEGER PRIMARY KEY, channel INTEGER)')
        if channel_id is not None:
            db.execute('INSERT OR REPLACE INTO welcome VALUES (?, ?)', (guild_id, channel_id))
        row = db.execute('SELECT channel FROM welcome WHERE guild = ?', (guild_id,)).fetchone()
        return row[0] if row else None


class Fighter(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents, allowed_mentions=discord.AllowedMentions.none())
        self.tree = app_commands.CommandTree(self)
        self.server_id = 0

    async def setup_hook(self):
        self.add_view(OpenTicket())
        self.add_view(CloseTicket())
        guild = discord.Object(id=self.server_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_ready(self):
        log.info('BE A FIGHTER is online as %s', self.user)
        try:
            await ensure_panel(self)
        except Exception:
            log.exception('Support panel could not be initialized')

    async def on_member_join(self, member):
        if member.guild.id != self.server_id or member.bot:
            return
        channel_id = setting(member.guild.id)
        channel = member.guild.get_channel(channel_id) if channel_id else None
        if isinstance(channel, discord.TextChannel):
            try:
                await channel.send(**welcome_message(member))
            except discord.HTTPException:
                log.exception('Could not send welcome; check channel permissions')


bot = Fighter()


def welcome_embed(member):
    embed = discord.Embed(
        title='NEW FIGHTER DETECTED', color=0x39D9FF,
        description=f'Welcome to **BE A FIGHTER**, {member.mention}.\n\n'
                    'I am **Sensei**, the voice of this world. Your arrival has been registered.\n\n'
                    'Read the rules, meet your fellow fighters, and begin your training. '
                    'Every legend starts with a first step. **Yours begins now.**',
        timestamp=discord.utils.utcnow())
    embed.set_author(name='ALERT ⚠️ ALERT ⚠️')
    embed.set_thumbnail(url=member.display_avatar.url)
    count = member.guild.member_count
    embed.add_field(name='TOTAL MEMBERS NOW', value=f'{count:,}' if count is not None else 'Updating…', inline=True)
    embed.add_field(name='SYSTEM STATUS', value='Arrival confirmed', inline=True)
    embed.set_image(url=WELCOME_GIF)
    embed.set_footer(text='BE A FIGHTER • Your journey is now in motion.')
    return embed


def welcome_message(member):
    # Mentions inside embeds do not notify members; ping only this arrival in content.
    return dict(content=f'✦ SYSTEM ANNOUNCEMENT · {member.mention}',
                embed=welcome_embed(member),
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, roles=False, users=[member], replied_user=False))


def target_error(actor, target, me, owner_id):
    if target.id in (actor.id, me.id, owner_id):
        return 'You cannot moderate yourself, this bot, or the server owner.'
    if actor.id != owner_id and target.top_role >= actor.top_role:
        return 'That member has an equal or higher role than you.'
    if target.top_role >= me.top_role:
        return 'Move my bot role above the target member’s role first.'
    return None


async def validate_target(interaction, member):
    error = target_error(interaction.user, member, interaction.guild.me, interaction.guild.owner_id)
    if error:
        raise app_commands.CheckFailure(error)


def audit_reason(interaction, reason):
    return f'{interaction.user} ({interaction.user.id}): {reason}'[:512]


@bot.tree.command(description='Show BE A FIGHTER bot commands.')
@app_commands.guild_only()
async def help(interaction: discord.Interaction):
    await interaction.response.send_message(
        '**SENSEI · WORLD SYSTEM**\nCommand registry online.\n\n/welcome_setup — choose welcome channel\n'
        '/welcome_test — preview welcome\n/timeout — timeout a member\n'
        '/untimeout — remove timeout\n/kick — kick a member\n/ban — ban a member\n'
        '/clear — delete recent messages (up to 100)\n'
        'Moderation requires the matching Discord permission and a higher role.', ephemeral=True)


@bot.tree.command(description='Choose the channel for new member welcome messages.')
@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_setup(interaction: discord.Interaction, channel: discord.TextChannel):
    permissions = channel.permissions_for(interaction.guild.me)
    if not (permissions.view_channel and permissions.send_messages and permissions.embed_links):
        raise app_commands.CheckFailure('I need View Channel, Send Messages, and Embed Links in that channel.')
    setting(interaction.guild_id, channel.id)
    await interaction.response.send_message(f'**SYSTEM CONFIGURED** · New fighter arrivals will be announced in {channel.mention}.', ephemeral=True)


@bot.tree.command(description='Privately preview the welcome message.')
@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome_test(interaction: discord.Interaction):
    preview = welcome_message(interaction.user)
    preview['allowed_mentions'] = discord.AllowedMentions.none()
    await interaction.response.send_message(**preview, ephemeral=True)


@bot.tree.command(description='Timeout a member for 1 minute to 28 days.')
@app_commands.guild_only()
@app_commands.default_permissions(moderate_members=True)
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.checks.bot_has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member,
                  minutes: app_commands.Range[int, 1, 40320], reason: app_commands.Range[str, 1, 300]):
    await validate_target(interaction, member)
    if member.guild_permissions.administrator:
        raise app_commands.CheckFailure('Discord does not allow timing out administrators.')
    await interaction.response.defer(ephemeral=True)
    await member.timeout(timedelta(minutes=minutes), reason=audit_reason(interaction, reason))
    await interaction.followup.send(f'**SYSTEM ACTION** · {member} has been timed out for {minutes} minutes.', ephemeral=True)


@bot.tree.command(description='Remove a member’s timeout.')
@app_commands.guild_only()
@app_commands.default_permissions(moderate_members=True)
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.checks.bot_has_permissions(moderate_members=True)
async def untimeout(interaction: discord.Interaction, member: discord.Member, reason: app_commands.Range[str, 1, 300]):
    await validate_target(interaction, member)
    await interaction.response.defer(ephemeral=True)
    await member.timeout(None, reason=audit_reason(interaction, reason))
    await interaction.followup.send(f'**SYSTEM ACTION** · Timeout lifted for {member}.', ephemeral=True)


@bot.tree.command(description='Kick a member from the server.')
@app_commands.guild_only()
@app_commands.default_permissions(kick_members=True)
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.checks.bot_has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: app_commands.Range[str, 1, 300]):
    await validate_target(interaction, member)
    await interaction.response.defer(ephemeral=True)
    await member.kick(reason=audit_reason(interaction, reason))
    await interaction.followup.send(f'**SYSTEM ACTION** · {member} has been kicked from the server.', ephemeral=True)


@bot.tree.command(description='Ban a member, keeping their existing messages.')
@app_commands.guild_only()
@app_commands.default_permissions(ban_members=True)
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.checks.bot_has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: app_commands.Range[str, 1, 300]):
    await validate_target(interaction, member)
    await interaction.response.defer(ephemeral=True)
    await member.ban(reason=audit_reason(interaction, reason), delete_message_seconds=0)
    await interaction.followup.send(f'**SYSTEM ACTION** · {member} has been banned from the server.', ephemeral=True)


@bot.tree.command(description='Delete up to 100 recent messages, excluding pinned messages.')
@app_commands.guild_only()
@app_commands.default_permissions(manage_messages=True)
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.checks.bot_has_permissions(manage_messages=True, read_message_history=True)
@app_commands.checks.cooldown(1, 10)
async def clear(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
    if not isinstance(interaction.channel, discord.TextChannel):
        raise app_commands.CheckFailure('Use this command in a server text channel.')
    await interaction.response.defer(ephemeral=True)
    cutoff = discord.utils.utcnow() - timedelta(days=14)
    deleted = await interaction.channel.purge(limit=amount, before=interaction.created_at,
        check=lambda message: not message.pinned and message.created_at > cutoff,
        reason=audit_reason(interaction, f'Clear requested: {amount}'))
    await interaction.followup.send(f'**SYSTEM CLEANUP** · Deleted {len(deleted)} messages. Pinned messages and messages older than 14 days were skipped.', ephemeral=True)


@bot.tree.error
async def command_error(interaction, error):
    original = getattr(error, 'original', error)
    if isinstance(error, app_commands.CheckFailure):
        message = str(error)
    elif isinstance(error, app_commands.CommandOnCooldown):
        message = f'Try again in {error.retry_after:.0f} seconds.'
    elif isinstance(original, discord.Forbidden):
        message = 'Discord denied this action. Check my permissions and role position.'
    elif isinstance(original, discord.HTTPException):
        message = 'Discord could not complete the request. Check the server before retrying.'
    else:
        log.error('Command failed', exc_info=(type(original), original, original.__traceback__))
        message = 'Something went wrong. Check the PyCharm console.'
    message = f'**SYSTEM NOTICE** · {message}'
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    token = os.getenv('DISCORD_TOKEN', '').strip()
    guild = os.getenv('DISCORD_GUILD_ID', '').strip()
    if not token or not guild.isdecimal() or int(guild) <= 0:
        raise SystemExit('Setup needed: copy .env.example to .env and fill DISCORD_TOKEN and DISCORD_GUILD_ID. See README.md.')
    bot.server_id = int(guild)
    bot.run(token)
