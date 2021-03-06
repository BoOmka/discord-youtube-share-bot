import typing as t
from datetime import datetime

from clients import YoutubeDataAPIv3AsyncClient
from enums import Definition
from models import Video


class YoutubeVideoRepository:
    def __init__(self, youtube_api_key: str):
        self._client = YoutubeDataAPIv3AsyncClient(youtube_api_key)

    async def get_many(self, video_ids: t.Collection[str]) -> t.List[Video]:
        if not video_ids:
            return []
        resp_json = await self._client.video_list(video_ids)
        videos = []
        for item in resp_json["items"]:
            videos.append(Video(
                id=item["id"],
                title=item["snippet"]["title"],
                published_at=datetime.strptime(item["snippet"]["publishedAt"], '%Y-%m-%dT%H:%M:%SZ'),
                definition=Definition[item["contentDetails"]["definition"]],
                has_maxresdefault="maxres" in item["snippet"]["thumbnails"],
            ))
        return videos

    async def get(self, video_id: str) -> Video:
        try:
            return (await self.get_many([video_id]))[0]
        except IndexError:
            raise ValueError("Video does not exist")

    async def get_video_or_none(self, video_id: str) -> t.Optional[Video]:
        try:
            return await self.get(video_id)
        except ValueError:
            return None
