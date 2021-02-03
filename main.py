import typing as t

import discord
import discord_slash.error
import pytube
import pytube.exceptions
import pytube.extract
from discord.ext import commands, tasks

from config import YT_API_KEY, DEVELOPER_ID, CHECK_VIDEO_LOOP_PERIOD_SECONDS, MAX_GETVIDEO_RETRIES, DISCORD_BOT_TOKEN
from helpers import suppress_expired_token_error, _send_video
from models import ScheduledVideo, Video
from repositories import YoutubeVideoRepository

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())
slash = discord_slash.SlashCommand(bot, auto_register=True)
yt_repo = YoutubeVideoRepository(YT_API_KEY)

SCHEDULED_POOL: t.Set['ScheduledVideo'] = set()

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
    check_videos.start()
    print('We have logged in as {0.user}'.format(bot))


@tasks.loop(seconds=CHECK_VIDEO_LOOP_PERIOD_SECONDS)
async def check_videos():
    global SCHEDULED_POOL
    sent_msgs = set()
    discarded_msgs = set()
    video_ids = [vid.video_id for vid in SCHEDULED_POOL]
    yt_videos: t.Dict[str, Video] = {vid.id: vid for vid in await yt_repo.get_many(video_ids)}
    for scheduled_video in SCHEDULED_POOL:
        yt_video = yt_videos.get(scheduled_video.video_id)
        if not yt_video:
            is_ready = False
        else:
            is_ready = yt_video.is_hd
            if not scheduled_video.is_availability_reported:
                await suppress_expired_token_error(
                    scheduled_video.ctx.send,
                    content=(
                        f"Ladies and gentlemen, we got it!\n"
                        f"Your video \"{yt_video.title}\" finally became available.\n"
                        f"Waiting 'till it reaches becomes HD..."
                    ),
                    complete_hidden=True
                )
                scheduled_video.is_availability_reported = True

        if is_ready:
            sent_msgs.add(scheduled_video)
            await _send_video(scheduled_video.ctx, yt_video.url)
        else:
            scheduled_video.retry_count += 1
            if scheduled_video.retry_count > MAX_GETVIDEO_RETRIES:
                discarded_msgs.add(scheduled_video)

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
    global SCHEDULED_POOL
    video_id = pytube.extract.video_id(link)
    if not video_id:
        await suppress_expired_token_error(
            ctx.send,
            content=f"This is not a valid YouTube video link!",
            complete_hidden=True
        )
        return
    try:
        video = await yt_repo.get(video_id)
    except ValueError:
        msg_content = (
            f"Ran into problem trying to retrieve the video (might be too new). "
            f"Anyways, will post it as soon as it will become available at HD!"
        )
        is_availability_reported = False
    except Exception:
        msg_content = f"Unexpected problem occured. <@{DEVELOPER_ID}> fix this shit!!!"
        await suppress_expired_token_error(ctx.send, content=msg_content, complete_hidden=False)
        return
    else:
        is_availability_reported = True
        if video.is_hd:
            msg_content = f'This video is already HD\nPosting immediately...'
            await suppress_expired_token_error(ctx.send, content=msg_content, complete_hidden=True)
            await _send_video(ctx, video.url)
            return
        else:
            msg_content = f'Alrighty. Will send "{video.title}" here as soon as it becomes HD!'

    SCHEDULED_POOL.add(ScheduledVideo(
        ctx=ctx,
        video_id=video_id,
        is_availability_reported=is_availability_reported,
    ))

    await suppress_expired_token_error(ctx.send, content=msg_content, complete_hidden=True)


if __name__ == '__main__':
    bot.run(DISCORD_BOT_TOKEN)
