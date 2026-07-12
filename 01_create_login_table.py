"""
01_create_login_table.py
Creates the 'login' DynamoDB table and seeds 10 user records.
Replace STUDENT_ID_PREFIX with your actual RMIT student ID (e.g. s3123456).
"""

import boto3
from botocore.exceptions import ClientError

# ── CONFIG ────────────────────────────────────────────────────────────────────
REGION          = "us-east-1"          # change to your AWS Academy region
STUDENT_PREFIX  = "s4077373"           # e.g. "s3123456"
FIRST_NAME      = "TANIYA"          # your first name
LAST_NAME       = "DASTAKEER"           # your last name
TABLE_NAME      = "login"
# ─────────────────────────────────────────────────────────────────────────────

dynamodb = boto3.resource("dynamodb", region_name=REGION)


def create_login_table():
    """Create the login table (email as PK, no sort key needed)."""
    try:
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "email", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "email", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        print(f"[OK] Table '{TABLE_NAME}' created.")
        return table
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"[SKIP] Table '{TABLE_NAME}' already exists.")
            return dynamodb.Table(TABLE_NAME)
        raise


def seed_users(table):
    """Insert 10 users as specified in the assignment."""
    passwords = ["demo-pw-1", "demo-pw-2", "demo-pw-3", "demo-pw-4", "demo-pw-5",
                "demo-pw-6", "demo-pw-7", "demo-pw-8", "demo-pw-9", "demo-pw-10"]

    with table.batch_writer() as batch:
        for i in range(10):
            item = {
                "email":     f"{STUDENT_PREFIX}{i}@student.rmit.edu.au",
                "user_name": f"{FIRST_NAME}{LAST_NAME}{i}",
                "password":  passwords[i],
            }
            batch.put_item(Item=item)
            print(f"  Inserted: {item['email']}")

    print(f"[OK] {10} users seeded into '{TABLE_NAME}'.")


if __name__ == "__main__":
    table = create_login_table()
    seed_users(table)
