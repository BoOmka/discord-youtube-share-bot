import logging
import typing as t
from datetime import datetime, timedelta

import discord
import discord_slash.error
import pytube
import pytube.exceptions
import pytube.extract
from discord.ext import commands, tasks

from config import (
    CHECK_VIDEO_LOOP_PERIOD_SECONDS,
    DEVELOPER_ID,
    DISCORD_BOT_TOKEN,
    LOG_LEVEL,
    MAX_GETVIDEO_RETRIES,
    VIDEO_AGE_FOR_HD_SECONDS, YT_API_KEY,
)
from enums import Definition
from helpers import _send_video, suppress_expired_token_error
from models import ScheduledVideo, Video
from repositories import YoutubeVideoRepository

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())
slash = discord_slash.SlashCommand(bot, sync_commands=True)
yt_repo = YoutubeVideoRepository(YT_API_KEY)

SCHEDULED_POOL: t.Set['ScheduledVideo'] = set()

logging.basicConfig()
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(LOG_LEVEL)

schedule_hd_options = [
    {
        'type': discord_slash.SlashCommandOptionType.STRING,
        'name': 'link',
        'description': 'Youtube video link',
        'required': True,
    }
]


@bot.event
async def on_ready():
    _LOGGER.info(f'Logged in as {bot.user}')
    check_videos.start()
    _LOGGER.info(f'Started `check_videos` task')


def is_video_hd(video: Video) -> bool:
    if video.definition is Definition.sd:
        return False
    if video.has_maxresdefault:
        return True
    video_age: timedelta = datetime.utcnow() - video.published_at
    if video_age.total_seconds() >= VIDEO_AGE_FOR_HD_SECONDS:
        return True
    return False


@tasks.loop(seconds=CHECK_VIDEO_LOOP_PERIOD_SECONDS)
async def check_videos():
    global SCHEDULED_POOL
    sent_msgs = set()
    discarded_msgs = set()
    video_ids = [vid.video_id for vid in SCHEDULED_POOL]
    yt_videos: t.Dict[str, Video] = {vid.id: vid for vid in await yt_repo.get_many(video_ids)}
    for scheduled_video in SCHEDULED_POOL:
        def log_attempt(sched_video: ScheduledVideo, postfix: str = "...") -> None:
            attempt = sched_video.retry_count + 1
            _LOGGER.info(f"{sched_video} (attempt #{attempt}) {postfix}")

        log_attempt(scheduled_video)
        yt_video = yt_videos.get(scheduled_video.video_id)
        if not yt_video:
            log_attempt(scheduled_video, "— Unavailable")
            is_ready = False
        else:
            is_ready = is_video_hd(yt_video)
            if not scheduled_video.is_availability_reported:
                await suppress_expired_token_error(
                    scheduled_video.ctx.send,
                    content=(
                        f"Ladies and gentlemen, we got it!\n"
                        f"Your video \"{yt_video.title}\" finally became available.\n"
                        f"Waiting 'till it reaches becomes HD..."
                    ),
                    hidden=True
                )
                scheduled_video.is_availability_reported = True

        if is_ready:
            log_attempt(scheduled_video, "— HD! Posting and removing from pool")
            sent_msgs.add(scheduled_video)
            await _send_video(scheduled_video.ctx, yt_video.url)
            _LOGGER.info(f"Posted video: {scheduled_video}")
        else:
            log_attempt(scheduled_video, "— Not HD")
            scheduled_video.retry_count += 1
            if scheduled_video.retry_count > MAX_GETVIDEO_RETRIES:
                log_attempt(scheduled_video, f"Max attempts ({MAX_GETVIDEO_RETRIES}) exceeded. Removing from pool")
                discarded_msgs.add(scheduled_video)
                msg_content = (
                    f"{scheduled_video.ctx.author.mention} want to send HD version of {scheduled_video.url}, "
                    f"but it never became HD."
                )
                embed = discord.Embed()
                embed.set_image(url="https://www.meme-arsenal.com/memes/8eaca408c8d818bb26575e2993c7b5ee.jpg")
                await suppress_expired_token_error(scheduled_video.ctx.channel.send, content=msg_content, embed=embed)

    SCHEDULED_POOL -= sent_msgs
    SCHEDULED_POOL -= discarded_msgs


@slash.subcommand(
    base="youtube",
    subcommand_group="schedule",
    name="hd",
    description='Post a video link as soon as it reaches its source resolution',
    options=schedule_hd_options,
)
async def schedule_hd(ctx: discord_slash.SlashContext, link: str):
    _LOGGER.info(f'New `schedule_hd` request: {link} (guild="{ctx.guild}", channel="{ctx.channel}")')
    global SCHEDULED_POOL
    await ctx.defer(hidden=True)
    try:
        video_id = pytube.extract.video_id(link)
    except pytube.exceptions.RegexMatchError:
        video_id = None
    if not video_id:
        await suppress_expired_token_error(
            ctx.send,
            content=f"This is not a valid YouTube video link!",
            hidden=True
        )
        _LOGGER.info(f'Rejected invalid link: {link} (guild="{ctx.guild}", channel="{ctx.channel}")')
        return
    try:
        video = await yt_repo.get(video_id)
    except ValueError:
        msg_content = (
            f"Ran into problem trying to retrieve the video (might be too new). "
            f"Anyways, will post it as soon as it will become available at HD!"
        )
        is_availability_reported = False
    except Exception as ex:
        _LOGGER.exception(ex)
        msg_content = f"Unexpected problem occured. <@{DEVELOPER_ID}> fix this shit!!!"
        await suppress_expired_token_error(ctx.send, content=msg_content,  hidden=True)
        return
    else:
        is_availability_reported = True
        if is_video_hd(video):
            msg_content = f'This video is already HD\nPosting immediately...'
            await suppress_expired_token_error(ctx.send, content=msg_content, hidden=True)
            await _send_video(ctx, video.url)
            _LOGGER.info(f'Posted link right-away: {link} (guild="{ctx.guild}", channel="{ctx.channel}")')
            return
        else:
            msg_content = f'Alrighty. Will send "{video.title}" here as soon as it becomes HD!'
            _LOGGER.info(f'Added link to pool: {link} (guild="{ctx.guild}", channel="{ctx.channel}")')

    SCHEDULED_POOL.add(ScheduledVideo(
        ctx=ctx,
        video_id=video_id,
        is_availability_reported=is_availability_reported,
    ))

    await suppress_expired_token_error(ctx.send, content=msg_content, hidden=True)


if __name__ == '__main__':
    bot.run(DISCORD_BOT_TOKEN)
