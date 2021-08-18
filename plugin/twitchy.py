import os
import tempfile
import webbrowser

from flox import Flox, ICON_SETTINGS, ICON_APP_ERROR, ICON_CANCEL
import requests
from twitch import TwitchClient, client
from streamlink import streams

from requests.exceptions import HTTPError

LIMIT = 10
FILTER_CHAR = ":"
GAMES_KEYWORD = "games"

class Twitchy(Flox):

    def __init__(self):
        self._client = None
        super().__init__()

    @property
    def client(self):
        if self._client is None:
            self._client = TwitchClient(self.settings.get('client_id'))
            try:
                self.client.ingests.get_server_list()
            except HTTPError:
                pass
        return self._client

    def search(self, query):
        try:
            channels = self.client.search.channels(query, limit=LIMIT)
            self.add_streams(channels)
        except TypeError:
            pass
        except HTTPError as e:
            self._add_except(e)
            self.add_item(
                title="Reset client ID",
                subtitle="This will wipe your client ID from settings.",
                icon=ICON_CANCEL,
                method='reset_settings'
            )

    @staticmethod
    def sort_channels(channel):
        return channel['views']

    @staticmethod
    def download(id, url):
        response = requests.get(url)
        if response.status_code == 200:
            temp_path = tempfile.gettempdir()
            save_dir = os.path.join(temp_path, 'twitchy')
            if not os.path.exists(save_dir):
                os.mkdir(save_dir)
            file_name = f"{id}.jpg"
            file_path = os.path.join(save_dir, file_name)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return file_path

    def add_games(self, games):
        for game in games:
            icon = self.download(game['id'], game['box']['small'])
            self.add_item(
                title=game['name'],
                icon=icon
            )

    def add_streams(self, channels):
        channels.sort(key=self.sort_channels, reverse=True)
        # self.logger.info(streams[0])
        # self.logger.info(self.client.streams.get_stream_by_user(streams[0]['id']))
        for channel in channels:
            stream = self.client.streams.get_stream_by_user(channel['id'])
            if stream:
                subtitle = f"[LIVE] Game: {stream['game']} - Viewers: {stream['viewers']} - {channel['status']}"
            else:
                subtitle = f"{channel['description']}"
            icon = self.download(channel['id'], channel['logo'])
            self.add_item(
                title=channel['display_name'],
                subtitle=subtitle,
                icon=icon,
                method='open_url',
                parameters=[channel['url']]
            )

    def following(self):
        username = self.settings['username']
        user_account_id = self.client.users.translate_usernames_to_ids([username])[0].id
        follows = self.client.users.get_follows(user_account_id, limit=LIMIT)
        # self.logger.info(follows)
        return follows

    def query(self, query):
        if not self.settings.get("client_id") or self.settings.get("client_id") == "":
            self.add_item(
                title=query,
                subtitle="Please enter your Twitch client token.",
                icon=ICON_SETTINGS,
                method='set_client_id',
                parameters=[query],
                hide=True
            )
        else:
            if query != '':
                self.search(query)
    
    def reset_settings(self):
        self.settings['_client_id'] = self.settings['client_id']
        self.settings['client_id'] = ""

    def set_client_id(self, client_id):
        try:
            self._client = TwitchClient(client_id)
            self.client.ingests.get_server_list()
        except HTTPError:
            self.show_msg(f"{self.name}: Client ID failed!", "Failed to connect to Twitch using client ID! Please try again!")
            self.settings['client_id'] = ""
        else:
            self.settings['client_id'] = client_id
            # self.show_msg(f"{self.name}: Success!!", f"{self.name} is now logged in!")
            self.change_query(f"{self.user_keyword} ", requery=True)


    def open_url(self, url):
        webbrowser.open(url)