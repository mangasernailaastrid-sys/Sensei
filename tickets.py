"""Persistent private support tickets for Sensei."""
import asyncio
import logging
import sqlite3
from pathlib import Path

import discord

PANEL_CHANNEL = 1571512402028003408
STAFF_ROLES = frozenset((1571479712453369916, 1571479796939231283))
DB = Path(__file__).resolve().parent / 'settings.db'
log = logging.getLogger('fighter.tickets')
lock = asyncio.Lock()


def db():
    con = sqlite3.connect(DB)
    con.execute('CREATE TABLE IF NOT EXISTS tickets (channel INTEGER PRIMARY KEY, guild INTEGER, creator INTEGER)')
    con.execute('CREATE TABLE IF NOT EXISTS ticket_panel (channel INTEGER PRIMARY KEY, message INTEGER)')
    return con


def is_staff(member):
    return any(role.id in STAFF_ROLES for role in member.roles)


def ticket_overwrites(guild, creator):
    roles = [guild.get_role(role_id) for role_id in STAFF_ROLES]
    if any(role is None for role in roles):
        raise RuntimeError('A configured support staff role is missing.')
    access = dict(view_channel=True, send_messages=True, read_message_history=True,
                  attach_files=True, embed_links=True)
    result = {guild.default_role: discord.PermissionOverwrite(view_channel=False),
              creator: discord.PermissionOverwrite(**access, manage_channels=False,
                  manage_roles=False, create_public_threads=False, create_private_threads=False),
              guild.me: discord.PermissionOverwrite(**access, manage_channels=True)}
    result.update({role: discord.PermissionOverwrite(**access) for role in roles})
    return result


class SafeView(discord.ui.View):
    async def on_error(self, interaction, error, item):
        log.error('Ticket action failed', exc_info=(type(error), error, error.__traceback__))
        text = '**SYSTEM NOTICE** · This action could not finish. Please ask staff to check Sensei’s permissions and try again.'
        if interaction.response.is_done():
            await interaction.followup.send(text, ephemeral=True)
        else:
            await interaction.response.send_message(text, ephemeral=True)


async def require_staff(interaction):
    if interaction.guild is None:
        return False
    member = await interaction.guild.fetch_member(interaction.user.id)
    if not is_staff(member):
        await interaction.response.send_message('**ACCESS DENIED** · Only City Founder or Community Team can close tickets.', ephemeral=True)
        return False
    with db() as con:
        row = con.execute('SELECT guild FROM tickets WHERE channel=?', (interaction.channel_id,)).fetchone()
    if row is None or row[0] != interaction.guild_id:
        await interaction.response.send_message('**SYSTEM NOTICE** · This is not a registered ticket.', ephemeral=True)
        return False
    return True


class ConfirmClose(SafeView):
    def __init__(self, staff_id):
        super().__init__(timeout=60)
        self.staff_id = staff_id

    @discord.ui.button(label='Delete Ticket', style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        if interaction.user.id != self.staff_id:
            await interaction.response.send_message('This confirmation belongs to another staff member.', ephemeral=True)
            return
        if not await require_staff(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        async with lock:
            # Restrict deletion to a recorded ticket, never an arbitrary channel.
            with db() as con:
                row = con.execute('SELECT guild FROM tickets WHERE channel=?', (interaction.channel_id,)).fetchone()
            if not row or row[0] != interaction.guild_id:
                return
            await interaction.channel.delete(reason=f'Sensei ticket closed by {interaction.user.id}')
            with db() as con:
                con.execute('DELETE FROM tickets WHERE channel=?', (interaction.channel_id,))
        self.stop()


class CloseTicket(SafeView):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Close Ticket', emoji='🔒', style=discord.ButtonStyle.danger,
                       custom_id='sensei:ticket:close:v1')
    async def close(self, interaction, button):
        if not await require_staff(interaction):
            return
        await interaction.response.send_message(
            '**END THIS TICKET?**\nThis permanently deletes the channel and its messages. No transcript is saved.',
            view=ConfirmClose(interaction.user.id), ephemeral=True)


class OpenTicket(SafeView):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Open Ticket', emoji='🎫', style=discord.ButtonStyle.primary,
                       custom_id='sensei:ticket:open:v1')
    async def open(self, interaction, button):
        if interaction.guild is None or interaction.channel_id != PANEL_CHANNEL:
            await interaction.response.send_message('Use the support panel to open a ticket.', ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        async with lock:
            guild = interaction.guild
            channels = await guild.fetch_channels()
            marker = f'sensei-ticket:v1:{interaction.user.id}'
            # Topics recover tickets even if the process stopped before saving SQLite.
            existing = next((c for c in channels if isinstance(c, discord.TextChannel) and c.topic == marker), None)
            if existing:
                with db() as con:
                    con.execute('INSERT OR REPLACE INTO tickets VALUES (?,?,?)', (existing.id, guild.id, interaction.user.id))
                await interaction.followup.send(f'**TICKET ALREADY OPEN** · {existing.mention}', ephemeral=True)
                return
            with db() as con:
                rows = con.execute('SELECT channel FROM tickets WHERE guild=? AND creator=?', (guild.id, interaction.user.id)).fetchall()
            existing = next((c for c in channels if c.id in {r[0] for r in rows}), None)
            if existing:
                await interaction.followup.send(f'**TICKET ALREADY OPEN** · {existing.mention}', ephemeral=True)
                return
            overwrites = ticket_overwrites(guild, interaction.user)
            channel = await guild.create_text_channel(
                name=f'ticket-{interaction.user.id}', topic=marker,
                overwrites=overwrites, reason=f'Support requested by {interaction.user.id}')
            with db() as con:
                con.execute('DELETE FROM tickets WHERE guild=? AND creator=?', (guild.id, interaction.user.id))
                con.execute('INSERT INTO tickets VALUES (?,?,?)', (channel.id, guild.id, interaction.user.id))
            embed = discord.Embed(title='SUPPORT CONNECTION ESTABLISHED', color=0x39D9FF,
                description=f'{interaction.user.mention}, your ticket is open.\n\n'
                            'Describe your issue and attach any useful screenshots or evidence. '
                            'City Founder and Community Team can assist you here.\n\n'
                            '**Only those staff roles can close this ticket using the button below.** '
                            'Closing permanently deletes this channel and its messages.')
            embed.set_author(name='ALERT ⚠️ ALERT ⚠️')
            embed.set_footer(text='SENSEI • Support system online')
            try:
                await channel.send(embed=embed, view=CloseTicket(), allowed_mentions=discord.AllowedMentions.none())
            except discord.HTTPException:
                # Roll back only the new, empty channel if its controls cannot be delivered.
                await channel.delete(reason='Ticket setup failed before control message was sent')
                with db() as con:
                    con.execute('DELETE FROM tickets WHERE channel=?', (channel.id,))
                raise
            await interaction.followup.send(f'**TICKET CREATED** · Continue in {channel.mention}.', ephemeral=True)


async def ensure_panel(client):
    async with lock:
        channel = await client.fetch_channel(PANEL_CHANNEL)
        if not isinstance(channel, discord.TextChannel) or channel.guild.id != client.server_id:
            raise RuntimeError('Support panel is not in the configured server.')
        with db() as con:
            row = con.execute('SELECT message FROM ticket_panel WHERE channel=?', (PANEL_CHANNEL,)).fetchone()
        embed = discord.Embed(title='BE A FIGHTER • SUPPORT', color=0x39D9FF,
            description='**Need assistance, fighter? Sensei is ready to connect you.**\n\n'
                        'Press **Open Ticket** to create a private support channel. '
                        'Explain your issue inside so City Founder and Community Team can help.\n\n'
                        '• One open ticket per member.')
        embed.set_author(name='ALERT ⚠️ ALERT ⚠️')
        embed.set_footer(text='SENSEI • Support system online')
        message = None
        if row:
            try:
                message = await channel.fetch_message(row[0])
            except discord.NotFound:
                pass
        if message:
            await message.edit(embed=embed, view=OpenTicket())
        else:
            message = await channel.send(embed=embed, view=OpenTicket(), allowed_mentions=discord.AllowedMentions.none())
            with db() as con:
                con.execute('INSERT OR REPLACE INTO ticket_panel VALUES (?,?)', (PANEL_CHANNEL, message.id))
        log.info('Support panel ready: %s', message.jump_url)
