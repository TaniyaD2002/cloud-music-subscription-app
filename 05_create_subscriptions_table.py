"""
05_create_subscriptions_table.py
Creates the 'subscriptions' DynamoDB table.

Key schema:
  PK = email                (String)  – who subscribed
  SK = title_artist_album   (String)  – which song (composite: title#artist#album)

This allows:
  - Fast lookup of all subscriptions for a user (PK query)
  - Exact removal of one subscription (PK + SK delete)
"""

import boto3
from botocore.exceptions import ClientError

REGION     = "us-east-1"
TABLE_NAME = "subscriptions"

dynamodb = boto3.client("dynamodb", region_name=REGION)


def create_subscriptions_table():
    try:
        dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "email",              "KeyType": "HASH"},
                {"AttributeName": "title_artist_album", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "email",              "AttributeType": "S"},
                {"AttributeName": "title_artist_album", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        waiter = dynamodb.get_waiter("table_exists")
        waiter.wait(TableName=TABLE_NAME)
        print(f"[OK] Table '{TABLE_NAME}' created.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"[SKIP] Table '{TABLE_NAME}' already exists.")
        else:
            raise


if __name__ == "__main__":
    create_subscriptions_table()
