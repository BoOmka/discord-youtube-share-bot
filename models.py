import dataclasses
from datetime import datetime

import discord_slash

from enums import Definition


@dataclasses.dataclass
class ScheduledVideo:
    ctx: discord_slash.SlashContext
    video_id: str
    retry_count: int = 0
    is_availability_reported: bool = False

    def __hash__(self):
        return hash((self.ctx.channel, self.ctx.author, self.video_id))

    def __repr__(self):
        return f'ScheduledVideo("{self.url}", guild="{self.ctx.guild}", channel="{self.ctx.channel}")'

    @property
    def url(self) -> str:
        return f"https://youtu.be/{self.video_id}"



@dataclasses.dataclass
class Video:
    id: str
    title: str
    published_at: datetime  # utc
    definition: Definition
    has_maxresdefault: bool

    @property
    def url(self) -> str:
        return f"https://youtu.be/{self.id}"
