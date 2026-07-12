"""
04_upload_images_s3.py
Downloads all unique artist images referenced in 2026a2_songs.json
and uploads them to an S3 bucket.

Prerequisites:
  - The S3 bucket must already exist (create via console or AWS CLI).
  - The IAM role must have s3:PutObject and s3:PutObjectAcl permissions.

Usage:
  python 04_upload_images_s3.py
"""

import json
import os
import urllib.request
from pathlib import Path

import boto3

REGION      = "us-east-1"
BUCKET_NAME = "taniya-music-app-2026"   # ← replace with your bucket name
JSON_FILE   = "2026a2_songs.json"
TMP_DIR     = Path("/tmp/artist_images")

s3 = boto3.client("s3", region_name=REGION)


def get_unique_images(json_file: str) -> dict[str, str]:
    """Return {filename: url} for each unique image URL in the dataset."""
    with open(json_file, "r", encoding="utf-8") as f:
        songs = json.load(f)["songs"]

    images = {}
    for song in songs:
        url      = song["img_url"]
        filename = url.split("/")[-1]   # e.g. "TaylorSwift.jpg"
        images[filename] = url
    return images


def download_image(url: str, dest: Path) -> None:
    headers = {"User-Agent": "Mozilla/5.0"}
    req     = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response, open(dest, "wb") as out:
        out.write(response.read())


def upload_to_s3(local_path: Path, s3_key: str) -> None:
    s3.upload_file(
        str(local_path),
        BUCKET_NAME,
        s3_key,
        ExtraArgs={"ContentType": "image/jpeg"},
    )


def main():
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    images = get_unique_images(JSON_FILE)
    print(f"Found {len(images)} unique artist images.")

    for filename, url in images.items():
        local_path = TMP_DIR / filename
        s3_key     = f"images/{filename}"

        # Download
        if not local_path.exists():
            print(f"  Downloading {filename} …", end=" ")
            try:
                download_image(url, local_path)
                print("done")
            except Exception as e:
                print(f"FAILED: {e}")
                continue
        else:
            print(f"  {filename} already cached locally.")

        # Upload
        print(f"  Uploading {filename} to s3://{BUCKET_NAME}/{s3_key} …", end=" ")
        try:
            upload_to_s3(local_path, s3_key)
            print("done")
        except Exception as e:
            print(f"FAILED: {e}")

    print("[OK] All images processed.")


if __name__ == "__main__":
    main()
