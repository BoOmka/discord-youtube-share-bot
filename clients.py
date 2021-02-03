import typing as t
import yarl

import aiohttp


class YoutubeDataAPIv3AsyncClient:
    base_url = yarl.URL("https://youtube.googleapis.com/youtube/v3/")

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session

    async def video_list(self, video_ids: t.Collection) -> t.Dict[str, t.Any]:
        url = self.base_url / "videos"
        url = url.update_query({
            "part": "snippet,contentDetails",
            "key": self._api_key,
            "id": ",".join(video_ids)
        })

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()
