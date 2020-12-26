import dataclasses
import os
import typing

import discord
import pytube
import pytube.exceptions
from discord.ext import commands, tasks
from discord_slash import SlashCommand, SlashContext
from pytube.extract import video_id

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
slash = SlashCommand(bot)

SCHEDULED_POOL: typing.Set['ScheduledByResolutionVideo'] = set()
CHECK_VIDEO_LOOP_PERIOD_SECONDS = 10
MAX_RETRIES = 1440  # max 14400 seconds / 4 hours


@dataclasses.dataclass
class ScheduledByResolutionVideo:
    ctx: SlashContext
    link: str
    resolution: int
    retry_count: int = 0
    is_availability_reported: bool = False
    max_available_resolution: typing.Optional[int] = None

    def __hash__(self):
        return hash((self.ctx.channel, self.ctx.author, self.link, self.resolution))


def parse_resolution(resolution_str: str) -> int:
    """Parse youtube video resolution string (e.g. `1080p`) to corresponding int"""
    return int(resolution_str.rstrip('p'))


@bot.event
async def on_ready():
    check_videos.start()
    print('We have logged in as {0.user}'.format(bot))


@tasks.loop(seconds=CHECK_VIDEO_LOOP_PERIOD_SECONDS)
async def check_videos():
    global SCHEDULED_POOL
    sent_msgs = set()
    discarded_msgs = set()
    for vid in SCHEDULED_POOL:
        try:
            video = pytube.YouTube(vid.link)
            max_resolution = max(parse_resolution(s.resolution) for s in video.streams if s.resolution is not None)
            is_ready = max_resolution >= vid.resolution
        except pytube.exceptions.VideoUnavailable:
            is_ready = False
        else:
            if not vid.is_availability_reported:
                await vid.ctx.channel.send(
                    f"Ladies and gentlemen, we got it! \"{video.title}\" finally became available @{max_resolution}p."
                    f"Waiting 'till it reaches {vid.resolution}p...",
                    complete_hidden=True
                )
                vid.is_availability_reported = True
                vid.max_available_resolution = max_resolution
            if vid.max_available_resolution is not None and max_resolution > vid.max_available_resolution:
                await vid.ctx.channel.send(f"\"{video.title}\": {max_resolution}p is available", complete_hidden=True)
                vid.max_available_resolution = max_resolution

        if is_ready:
            sent_msgs.add(vid)
            await vid.ctx.channel.send(f"{vid.ctx.author.mention}: {vid.link}")
        else:
            vid.retry_count += 1
            if vid.retry_count > MAX_RETRIES:
                discarded_msgs.add(vid)

    SCHEDULED_POOL -= sent_msgs
    SCHEDULED_POOL -= discarded_msgs


@slash.subcommand(base="youtube", subcommand_group="schedule", name="resolution")
async def schedule_resolution(ctx: SlashContext, link: str, resolution: int = 1080):
    global SCHEDULED_POOL
    try:
        video = pytube.YouTube(link)
    except pytube.extract.RegexMatchError:
        await ctx.send(content=f"This is not a valid YouTube video link!", complete_hidden=True)
        return
    except pytube.exceptions.VideoUnavailable:
        msg_content = (
            f"Ran into problem trying to retrieve the video (might be too new). "
            f"Anyways, will post it as soon as it will become available at {resolution}p!"
        )
        watch_url = link
        is_availability_reported = False
    else:
        msg_content = f'Alrighty. Will send "{video.title}" here as soon as its quality reaches {resolution}p!'
        watch_url = video.watch_url
        is_availability_reported = True

    SCHEDULED_POOL.add(ScheduledByResolutionVideo(
        ctx=ctx,
        link=watch_url,
        resolution=resolution,
        is_availability_reported=is_availability_reported,
    ))
    await ctx.send(content=msg_content, complete_hidden=True)


if __name__ == '__main__':
    bot.run(os.environ.get('DISCORD_TOKEN'))
