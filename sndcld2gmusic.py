#!/usr/bin/env python3

__prog__ = 'sndcld2gmusic'

import sys
import os


import argparse
import configparser
import re
from pprint import pprint

from mutagen.easyid3 import EasyID3
from soundscrape import soundscrape as sc
from gmusicapi import Mobileclient, Musicmanager, clients as gmclients


class Track(object):

    def __init__(self, path):
        self.title
        self.artist
        self.length
        self.filename


def sc_download(url_playlist: str, path: str) -> list:
    args_sc = {
        'artist_url': url_playlist,
        'path': path,
        'track': None,
        'keep': False,
        'folders': False,
        'num_tracks': sys.maxsize,
        'downloadable': False,
        'open': False
    }
    sc.process_soundcloud(args_sc)

def get_tags(path: str) -> tuple:
    s = EasyID3(path)
    return s['title'][0], ','.join(s['artist'])


def gm_get_current_pl_member(client: Mobileclient, playlist: str) -> (str, list):
    playlist = list(filter(
        lambda x: x['deleted'] == False and x['name'] == playlist,
        client.get_all_user_playlist_contents()
    ))[0]
    member_track_ids = set([item['trackId'] for item in playlist['tracks']])
    return playlist['id'], [item for item in client.get_all_songs() if item['id'] in member_track_ids]


def gm_extract_id(upload_resp: tuple):
    if upload_resp[0] != {}:
        return list(upload_resp[0].items())[0][1]
    if upload_resp[1] != {}:
        return list(upload_resp[1].items())[0][1]
    if upload_resp[2] != {}:
        return re.search(r'.+\((.+)\)', list(upload_resp[2].items())[0][1]).group(1)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Syncs your soundcloud likes with your gmusic and puts the tracks in a playlists',
        prog=__prog__)
    parser.add_argument(
        '-c',
        type=str,
        nargs='?',
        dest='config',
        default='config.ini',
        required=False,
        help='Path to config')

    return parser.parse_args()


def parse_conf(path_config: str) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    try:
        cfg.read(path_config)
    except FileNotFoundError as e:
        sys.stderr.write('File {} not found'.format(path_config))
        sys.exit(1)
    return cfg


def init() -> (argparse.Namespace,configparser.ConfigParser):
    args = parse_args()
    config = parse_conf(args.config)
    return args, config

def main():
    args, config = init()

    if not os.path.isdir(config['PROG']['DownloadPath']):
        os.mkdir(config['PROG']['DownloadPath'])

    sc_download(
        config['SOUNDCLOUD']['PlaylistUrl'],
        config['PROG']['DownloadPath']
    )

    mc = Mobileclient()
    mc.login(config['GMUSIC']['User'], config['GMUSIC']['Password'], Mobileclient.FROM_MAC_ADDRESS)

    mm = Musicmanager()
    if not (os.path.exists(gmclients.OAUTH_FILEPATH) and mm.login(gmclients.OAUTH_FILEPATH)):
        mm.perform_oauth(gmclients.OAUTH_FILEPATH, open_browser=True)
        if not mm.login(gmclients.OAUTH_FILEPATH):
            sys.stderr.write('Musicmanager could not authenticate')

    if config['GMUSIC']['TargetPlaylist'] not in set([item['name'] for item in mc.get_all_playlists() if not item['deleted']]):
        mc.create_playlist(name=config['GMUSIC']['TargetPlaylist'], description='Tracks synchronized using {}'.format(__prog__), public=False)

    playlist_id, current_members = gm_get_current_pl_member(mc, config['GMUSIC']['TargetPlaylist'])

    for track in os.listdir(config['PROG']['DownloadPath']):
        print('Uploading {}'.format(track))
        uploaded_id = gm_extract_id(mm.upload('{}{}'.format(config['PROG']['DownloadPath'], track)))
        mc.add_songs_to_playlist(playlist_id, uploaded_id)

if '__main__' == __name__:
    main()
