import dataclasses
import os
import typing

import discord
import pytube
from discord.ext import commands, tasks
from discord_slash import SlashCommand, SlashContext
from pytube.extract import video_id

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
slash = SlashCommand(bot)

SCHEDULED_POOL: typing.Set['ScheduledByResolutionVideo'] = set()


def check_video(link: str, resolution: int) -> bool:
    video = pytube.YouTube(link)
    max_resolution = max(parse_resolution(s.resolution) for s in video.streams if s.resolution is not None)
    return max_resolution >= resolution


@dataclasses.dataclass
class ScheduledByResolutionVideo:
    channel: discord.TextChannel
    author: discord.User
    link: str
    resolution: int

    def __hash__(self):
        return hash((self.channel, self.author, self.link, self.resolution))


def parse_resolution(resolution_str: str) -> int:
    """Parse youtube video resolution string (e.g. `1080p`) to corresponding int"""
    return int(resolution_str.rstrip('p'))


@bot.event
async def on_ready():
    check_videos.start()
    print('We have logged in as {0.user}'.format(bot))


@tasks.loop(seconds=10)
async def check_videos():
    global SCHEDULED_POOL
    sent_msgs = set()
    for vid in SCHEDULED_POOL:
        if check_video(link=vid.link, resolution=vid.resolution):
            sent_msgs.add(vid)
            await vid.channel.send(f"{vid.author.mention}: {vid.link}")

    SCHEDULED_POOL -= sent_msgs


@slash.subcommand(base="youtube", subcommand_group="schedule", name="resolution")
async def schedule_resolution(ctx: SlashContext, link: str, resolution: int = 1080):
    global SCHEDULED_POOL
    try:
        video = pytube.YouTube(link)
    except pytube.extract.RegexMatchError:
        await ctx.send(content=f"This is not a valid YouTube video link!", complete_hidden=True)
        return

    SCHEDULED_POOL.add(ScheduledByResolutionVideo(
        channel=ctx.channel,
        author=ctx.author,
        link=video.watch_url,
        resolution=resolution,
    ))
    await ctx.send(
        content=f'Alrighty. Will send "{video.title}" here as soon as its quality reaches {resolution}p!',
        complete_hidden=True,
    )


if __name__ == '__main__':
    bot.run(os.environ.get('DISCORD_TOKEN'))
