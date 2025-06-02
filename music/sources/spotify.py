import discord
import lavalink
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from utils import config

sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=config.spotify["client_id"],
        client_secret=config.spotify["client_secret"],
        cache_handler=spotipy.cache_handler.MemoryCacheHandler(),
    )
)


class SpotifyAudioTrack(lavalink.DeferredAudioTrack):
    async def load(self, client: discord.Bot):
        result: lavalink.LoadResult = await client.get_tracks(f"ytsearch:{self.title} {self.author}")
        if result.load_type != lavalink.LoadType.SEARCH or not result.tracks:
            raise lavalink.LoadError
        first_track = result.tracks[0]
        base64 = first_track.track
        self.track = base64
        return base64


class SpotifySource(lavalink.Source):
    def __init__(self, url: str, requester: int):
        self.url = url
        self.requester = requester
        super().__init__(name="spotify")

    # Spotify source
    async def get(self):
        return {"playlist": sp.playlist, "album": sp.album, "track": sp.track}.get(
            self.url.split("/")[-2], lambda _: None
        )(self.url)

    # Load playlist
    async def _load_pl(self) -> tuple[list[SpotifyAudioTrack], lavalink.PlaylistInfo]:
        pl = await self.get()
        tracks = []
        for track in pl["tracks"]["items"]:
            tracks.append(
                SpotifyAudioTrack(
                    {
                        "identifier": track["track"]["id"],
                        "isSeekable": True,
                        "author": ", ".join([artist["name"] for artist in track["track"]["artists"]]),
                        "length": track["track"]["duration_ms"],
                        "isStream": False,
                        "title": track["track"]["name"],
                        "uri": track["track"]["external_urls"]["spotify"],
                        "sourceName": "spotify",
                    },
                    requester=self.requester,
                    cover=track["track"]["album"]["images"][0]["url"],
                )
            )
        pl_info = lavalink.PlaylistInfo(name=pl["name"])
        return tracks, pl_info

    # Load album
    async def _load_al(self) -> tuple[list[SpotifyAudioTrack], lavalink.PlaylistInfo]:
        al = await self.get()
        tracks = []
        for track in al["tracks"]["items"]:
            tracks.append(
                SpotifyAudioTrack(
                    {
                        "identifier": track["id"],
                        "isSeekable": True,
                        "author": ", ".join([artist["name"] for artist in track["artists"]]),
                        "length": track["duration_ms"],
                        "isStream": False,
                        "title": track["name"],
                        "uri": track["external_urls"]["spotify"],
                        "sourceName": "spotify",
                    },
                    requester=self.requester,
                    cover=track["album"]["images"][0]["url"],
                )
            )
        pl_info = lavalink.PlaylistInfo(name=al["name"])
        return tracks, pl_info

    # Load track
    async def _load_track(self) -> SpotifyAudioTrack:
        track = await self.get()
        return SpotifyAudioTrack(
            {
                "identifier": track["id"],
                "isSeekable": True,
                "author": ", ".join([artist["name"] for artist in track["artists"]]),
                "length": track["duration_ms"],
                "isStream": False,
                "title": track["name"],
                "uri": track["external_urls"]["spotify"],
                "sourceName": "spotify",
            },
            requester=self.requester,
            cover=track["album"]["images"][0]["url"],
        )

    # Load items
    async def load_item(self, client: discord.Bot):
        if "playlist" in self.url:
            pl, pl_info = await self._load_pl()
            return lavalink.LoadResult(lavalink.LoadType.PLAYLIST, pl, pl_info)
        if "album" in self.url:
            al, al_info = await self._load_al()
            return lavalink.LoadResult(lavalink.LoadType.PLAYLIST, al, al_info)
        if "track" in self.url:
            track = await self._load_track()
            return lavalink.LoadResult(lavalink.LoadType.TRACK, [track], lavalink.PlaylistInfo.none())
