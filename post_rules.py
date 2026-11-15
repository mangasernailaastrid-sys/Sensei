"""Publish Sensei's rules once, or update the previously published message."""
import asyncio
import json
import os
from pathlib import Path

import discord
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
CHANNEL_ID = 1571477452180557834
RECEIPT = ROOT / '.tmp' / 'rules-message.json'


def rules_embed():
    embed = discord.Embed(
        title='BE A FIGHTER • SERVER RULES',
        description='**Fighter, your access to this world comes with responsibility.**\n'
                    'I am Sensei. Read these rules before entering the conversation. '
                    'Train hard, compete fairly, and respect the community.',
        color=0x39D9FF)
    embed.set_author(name='ALERT ⚠️ ALERT ⚠️')
    rules = [
        ('01 • RESPECT EVERY FIGHTER',
         'No harassment, hate speech, slurs, threats, or targeted bullying. '
         'Keep rivalry friendly. Stop if someone asks you to stop.'),
        ('02 • KEEP THE SERVER SAFE',
         'No sexual or explicit content, graphic gore, or disturbing material. '
         'Keep names, avatars, messages, and uploads appropriate for the community.'),
        ('03 • FIGHT FAIR',
         'No cheating, exploits, scripts, or instructions for abusing bugs. '
         'Report vulnerabilities privately to staff instead of sharing them publicly.'),
        ('04 • NO SPAM OR DISRUPTION',
         'No message flooding, repeated pings, raids, or disruptive voice-chat audio. '
         'Use the correct channels and keep conversations on topic.'),
        ('05 • NO SCAMS OR UNAPPROVED PROMOTION',
         'No phishing, suspicious downloads, account trading, or fake giveaways. '
         'Ask staff before advertising servers, products, or services.'),
        ('06 • PROTECT PERSONAL INFORMATION',
         'Do not share anyone’s private information, passwords, tokens, or private conversations '
         'without permission. Never impersonate staff or other members.'),
        ('07 • REPORT PROBLEMS RESPONSIBLY',
         'Send reports and relevant evidence privately to staff. '
         'No public witch hunts, false reports, or retaliation. Dispute moderation decisions calmly and privately.'),
        ('08 • FOLLOW STAFF DIRECTION',
         'Follow Discord’s and Roblox’s rules, plus reasonable staff instructions. '
         'Do not evade moderation with alternate accounts or look for loopholes.'),
    ]
    for name, value in rules:
        embed.add_field(name=name, value=value, inline=False)
    embed.add_field(
        name='⚠️ SYSTEM ENFORCEMENT',
        value='Violations may result in a warning, message removal, timeout, kick, or ban, '
              'depending on severity and repetition. Serious violations may lead to an immediate ban.',
        inline=False)
    embed.set_footer(text='SENSEI • Respect the world. Respect the fighters.')
    return embed


async def main():
    load_dotenv(ROOT / '.env')
    async with discord.Client(intents=discord.Intents.none(),
                              allowed_mentions=discord.AllowedMentions.none()) as client:
        await client.login(os.environ['DISCORD_TOKEN'].strip())
        channel = await client.fetch_channel(CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            raise RuntimeError('Destination must be a server text channel.')
        if channel.guild.id != int(os.environ['DISCORD_GUILD_ID']):
            raise RuntimeError('Destination is not in the configured server.')
        embed = rules_embed()
        if len(embed) > 6000:
            raise RuntimeError('Rules exceed Discord embed limits.')
        if RECEIPT.exists():
            receipt = json.loads(RECEIPT.read_text())
            if receipt['channel_id'] != CHANNEL_ID:
                raise RuntimeError('Saved receipt is for a different channel.')
            message = await channel.fetch_message(receipt['message_id'])
            if message.author.id != client.user.id:
                raise RuntimeError('Saved message is not owned by Sensei.')
            await message.edit(embed=embed, allowed_mentions=discord.AllowedMentions.none())
        else:
            message = await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
            RECEIPT.parent.mkdir(exist_ok=True)
            RECEIPT.write_text(json.dumps({'channel_id': CHANNEL_ID, 'message_id': message.id}))
        verified = await channel.fetch_message(message.id)
        assert verified.embeds[0].title == embed.title
        assert len(verified.embeds[0].fields) == 9
        print('Rules embed verified:', verified.jump_url)


if __name__ == '__main__':
    asyncio.run(main())
