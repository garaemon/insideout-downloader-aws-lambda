#!/usr/bin/env python

# yapf: disable
import sys
import stat
import shutil
import subprocess
import re
import json
import os
import glob
from datetime import datetime, timedelta

if not 'HOME' in os.environ:
    os.environ['HOME'] = '/tmp'

from slack_webhook import Slack
from ytmusicapi import YTMusic
import urllib.request
import arrow
import mutagen
from mutagen.easyid3 import EasyID3
import boto3
from bs4 import BeautifulSoup
# yapf: enable

INSIDEOUT_URL = 'https://block.fm/radio/insideout'

def download(this_week=True):
    response = urllib.request.urlopen(INSIDEOUT_URL)
    data = response.read()
    soup = BeautifulSoup(data, "html.parser")
    next_data = soup.find(id="__NEXT_DATA__")
    json_data = json.loads(next_data.text)
    episodes = json_data["props"]["pageProps"]["episodes"]["edges"]
    for e in episodes:
        episode_info = e["node"]["acfEpisode"]
        date_str = episode_info["dateStart"]
        print('date_str', date_str)
        started_at = arrow.get(date_str).replace(tzinfo='Asia/Tokyo')
        mp3_url = episode_info["archiveUrl"]
        if not mp3_url:
            continue
        if this_week:
            today = arrow.now()
            diff = today - started_at
            print(diff)
            # diff should be positive because sound_source can have future date.
            if diff >= timedelta(days=7) or diff < timedelta(days=0):
                print('Skipping entory for', date_str)
                continue
            else:
                print('Downloading entory for', date_str)

        title = '{0:04d}{1:02d}{2:02d}-insideout'.format(started_at.year,
                                                         started_at.month,
                                                         started_at.day)
        output_filename = os.path.join('/tmp', title + '.mp3')
        print('Downloading mp3 file from {}'.format(mp3_url))
        urllib.request.urlretrieve(mp3_url, output_filename)
        try:
            tags = EasyID3(output_filename)
        except mutagen.id3.ID3NoHeaderError:
            tags = mutagen.File(output_filename, easy=True)
            tags.add_tags()
        tags['title'] = title
        tags['artist'] = '渡辺志保 & DJ YANATAKE'
        tags['album'] = 'insideout {0:04d}'.format(started_at.year)
        tags['tracknumber'] = str(started_at.week)
        tags.save()
    return output_filename

def upload_to_youtube_music(mp3file):
    ytmusic = YTMusic('ytmusic_headers_auth.json')
    ytmusic.upload_song(mp3file)


def upload_to_google_drive(filename, upload_directory):
    # copy token cache
    shutil.copyfile('skicka.tokencache.json', '/tmp/skicka.tokencache.json')
    shutil.copyfile('skicka.config', '/tmp/skicka.config')
    # read and write = 6
    os.chmod('/tmp/skicka.tokencache.json', stat.S_IREAD | stat.S_IWRITE)
    os.chmod('/tmp/skicka.config', stat.S_IREAD | stat.S_IWRITE)
    subprocess.check_call([
        'skicka',
        '-config',
        '/tmp/skicka.config',
        '-tokencache',
        '/tmp/skicka.tokencache.json',
        '-metadata-cache-file',
        '/tmp/skicka.metadata',
        'upload',
        filename,
        upload_directory,
    ])


def upload_to_s3(filename, upload_directory):
    bucket = os.environ['S3_BUCKET']
    s3 = boto3.resource('s3')
    bucket_client = s3.Bucket(bucket)
    target_path = os.path.join(upload_directory, os.path.basename(filename))
    print('filename', filename)
    print('upload_directory', upload_directory)
    print('target', target_path)
    bucket_client.upload_file(filename,  target_path)


def lambda_handler(event, context):
    print('add current working directory to PATH')
    slack = Slack(url=os.environ['SLACK_WEBHOOK_URL'])
    os.environ['PATH'] = os.environ['PATH'] + ':' + os.path.dirname(
        os.path.abspath(__file__)) + ':' + os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'bin')
    try:
        mp3file_name = download(this_week=True)
        upload_to_s3(mp3file_name,
                     os.environ['UPLOAD_GOOGLE_DRIVE_DIRECTORY'])
        upload_to_google_drive(mp3file_name,
                               os.environ['UPLOAD_GOOGLE_DRIVE_DIRECTORY'])
        upload_to_youtube_music(mp3file_name)
        slack.post(text='[insideout] :tada: done recording insideout')
    except Exception as e:
        slack.post(text='[insideout] :red_circle: failed to record insideout')
        raise e

    # run radirec
    return {
        'isBase64Encoded': False,
        'statusCode': 200,
        'headers': {},
        'body': '{"message": "Hello from AWS Lambda"}'
    }


if __name__ == '__main__':
    download(this_week=False)
