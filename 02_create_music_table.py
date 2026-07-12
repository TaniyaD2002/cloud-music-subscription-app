"""
02_create_music_table.py
Creates the 'music' DynamoDB table with a composite sort key and
one GSI + one LSI as required by the assignment.

Key schema rationale:
  The dataset has songs where:
    - Same title appears with different artists (e.g. "Bad Blood")
    - Same title+artist appears in different albums (e.g. "Delicate" by Taylor Swift)
  Therefore title alone cannot be the PK, and artist alone cannot be the SK.

  Chosen schema:
    PK  = title         (String)
    SK  = artist_album  (String, value = f"{artist}#{album}")

  This guarantees every song record is uniquely addressable.

Indexes:
  GSI  "artist-year-index":  PK=artist,  SK=year
       → supports queries like "all songs by Jimmy Buffett in 1974"
  LSI  "title-year-index":   PK=title,   SK=year
       → supports range queries on year within a title partition
"""

import boto3
from botocore.exceptions import ClientError

REGION     = "us-east-1"
TABLE_NAME = "music"

dynamodb = boto3.client("dynamodb", region_name=REGION)


def create_music_table():
    try:
        response = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "title",        "KeyType": "HASH"},
                {"AttributeName": "artist_album",  "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "title",        "AttributeType": "S"},
                {"AttributeName": "artist_album",  "AttributeType": "S"},
                {"AttributeName": "artist",        "AttributeType": "S"},
                {"AttributeName": "year",          "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",

            # ── GSI: query by artist (+ optionally year) ──────────────────────
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "artist-year-index",
                    "KeySchema": [
                        {"AttributeName": "artist", "KeyType": "HASH"},
                        {"AttributeName": "year",   "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],

            # ── LSI: range query on year within a title partition ─────────────
            LocalSecondaryIndexes=[
                {
                    "IndexName": "title-year-index",
                    "KeySchema": [
                        {"AttributeName": "title", "KeyType": "HASH"},
                        {"AttributeName": "year",  "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        )
        # Wait for the table to become active
        waiter = dynamodb.get_waiter("table_exists")
        waiter.wait(TableName=TABLE_NAME)
        print(f"[OK] Table '{TABLE_NAME}' created.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"[SKIP] Table '{TABLE_NAME}' already exists.")
        else:
            raise


if __name__ == "__main__":
    create_music_table()
