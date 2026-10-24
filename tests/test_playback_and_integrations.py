import unittest
from unittest import mock
from app.api.playback_api import PlaybackAPIMixin
from app.api.system_api import SystemAPIMixin
from discord_rpc import DiscordRPC


class DummyApp:
    def __init__(self):
        self.media_listener = mock.MagicMock()
        self.discord_rpc = DiscordRPC()
        self.lyrics_service = mock.MagicMock()
        self.lyrics_service.cache.get_setting.return_value = ""


class PlaybackAndIntegrationsTestCase(unittest.TestCase):
    def setUp(self):
        self.api = PlaybackAPIMixin()
        self.api._app = DummyApp()
        self.sys_api = SystemAPIMixin()
        self.sys_api._app = self.api._app

    def test_adjust_volume_with_spotify_session(self):
        with mock.patch("pycaw.pycaw.AudioUtilities.GetAllSessions") as mock_get_sessions:
            mock_session = mock.MagicMock()
            mock_session.Process.name.return_value = "Spotify.exe"
            mock_vol = mock.MagicMock()
            mock_vol.GetMasterVolume.return_value = 0.50
            mock_session._ctl.QueryInterface.return_value = mock_vol
            mock_get_sessions.return_value = [mock_session]

            res = self.api.adjust_volume(1)
            self.assertEqual(res["target"], "spotify")
            self.assertEqual(res["volume"], 55)
            mock_vol.SetMasterVolume.assert_called_once_with(0.55, None)

    def test_adjust_volume_fallback_when_no_spotify(self):
        with mock.patch("pycaw.pycaw.AudioUtilities.GetAllSessions") as mock_get_sessions:
            mock_get_sessions.return_value = []
            with mock.patch("ctypes.windll.user32.keybd_event") as mock_keybd:
                res = self.api.adjust_volume(-1)
                self.assertEqual(res["target"], "master")
                self.assertEqual(mock_keybd.call_count, 2)

    def test_get_spotify_queue_without_token(self):
        self.api._app.lyrics_service.cache.get_setting.return_value = ""
        res = self.api.get_spotify_queue()
        self.assertFalse(res["connected"])
        self.assertEqual(res["items"], [])

    def test_get_spotify_queue_with_mocked_api_response(self):
        self.api._app.lyrics_service.cache.get_setting.return_value = "fake_token_123"
        with mock.patch("urllib.request.urlopen") as mock_open:
            mock_resp = mock.MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = b'{"queue": [{"name": "Song A", "duration_ms": 195000, "artists": [{"name": "Artist A"}], "album": {"name": "Album A", "images": [{"url": "http://img.jpg"}]}}]}'
            mock_resp.__enter__.return_value = mock_resp
            mock_open.return_value = mock_resp

            res = self.api.get_spotify_queue()
            self.assertTrue(res["connected"])
            self.assertEqual(len(res["items"]), 1)
            self.assertEqual(res["items"][0]["title"], "Song A")
            self.assertEqual(res["items"][0]["artist"], "Artist A")
            self.assertEqual(res["items"][0]["duration_seconds"], 195)

    def test_set_and_get_volume_with_spotify(self):
        with mock.patch("pycaw.pycaw.AudioUtilities.GetAllSessions") as mock_get_sessions:
            mock_session = mock.MagicMock()
            mock_session.Process.name.return_value = "Spotify.exe"
            mock_vol = mock.MagicMock()
            mock_vol.GetMasterVolume.return_value = 0.80
            mock_session._ctl.QueryInterface.return_value = mock_vol
            mock_get_sessions.return_value = [mock_session]

            set_res = self.api.set_volume(80)
            self.assertEqual(set_res["target"], "spotify")
            self.assertEqual(set_res["volume"], 80)
            mock_vol.SetMasterVolume.assert_called_once_with(0.80, None)

            get_res = self.api.get_volume()
            self.assertEqual(get_res["volume"], 80)

    def test_discord_rpc_client_id_update(self):
        rpc = DiscordRPC("123456")
        self.assertEqual(rpc.client_id, "123456")
        rpc.set_client_id("987654")
        self.assertEqual(rpc.client_id, "987654")


if __name__ == "__main__":
    unittest.main()
