"""
03_load_music.py
Loads all songs from 2026a2_songs.json into the 'music' DynamoDB table.

The composite sort key  artist_album = f"{artist}#{album}"  ensures that
no two songs can overwrite each other even when they share the same title.
"""

import json
import boto3
from decimal import Decimal

REGION     = "us-east-1"
TABLE_NAME = "music"
JSON_FILE  = "2026a2_songs.json"   # path relative to this script

dynamodb = boto3.resource("dynamodb", region_name=REGION)


def load_songs():
    table = dynamodb.Table(TABLE_NAME)

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    songs = data["songs"]
    print(f"Loading {len(songs)} songs …")

    with table.batch_writer() as batch:
        for song in songs:
            item = {
                "title":        song["title"],
                "artist_album": f"{song['artist']}#{song['album']}",  # composite SK
                "artist":       song["artist"],
                "year":         song["year"],
                "album":        song["album"],
                "image_url":    song["img_url"],
            }
            batch.put_item(Item=item)

    print(f"[OK] {len(songs)} songs loaded into '{TABLE_NAME}'.")


if __name__ == "__main__":
    load_songs()
