import os

DISCORD_BOT_TOKEN = os.environ.get('DISCORD_TOKEN')
YT_API_KEY = os.environ.get("YOUTUBE_API_KEY")
DEVELOPER_ID = os.environ.get("DISCORD_BOT_DEVELOPER_ID", None)
CHECK_VIDEO_LOOP_PERIOD_SECONDS = 20
MAX_GETVIDEO_RETRIES = 4 * 60 * 60 / CHECK_VIDEO_LOOP_PERIOD_SECONDS  # max 4 hours
LOG_LEVEL = "DEBUG"
VIDEO_AGE_FOR_HD_SECONDS = 1.5 * 60 * 60  # 1.5 hours
