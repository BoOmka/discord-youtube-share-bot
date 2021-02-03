import dataclasses

import discord_slash


@dataclasses.dataclass
class ScheduledVideo:
    ctx: discord_slash.SlashContext
    video_id: str
    retry_count: int = 0
    is_availability_reported: bool = False

    def __hash__(self):
        return hash((self.ctx.channel, self.ctx.author, self.video_id))


@dataclasses.dataclass
class Video:
    id: str
    title: str
    is_hd: bool

    @property
    def url(self) -> str:
        return f"https://youtu.be/{self.id}"
