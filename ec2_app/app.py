from flask_cors import CORS
"""
ec2_app/app.py
Flask backend for the music subscription app.
Deploy this on EC2 (directly) or ECS (via Docker).

Environment variables expected:
  AWS_REGION      (default: us-east-1)
  S3_BUCKET       name of your images bucket
  SECRET_KEY      random string for Flask sessions

Run locally:  python app.py
Production:   gunicorn -w 4 -b 0.0.0.0:80 app:app
"""

import os
import boto3
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from boto3.dynamodb.conditions import Key, Attr
from functools import wraps

REGION     = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET  = os.environ.get("S3_BUCKET",  "taniya-music-app-2026")
SECRET_KEY = os.environ.get("SECRET_KEY", "anyrandomstring123")

app = Flask(__name__)
app.secret_key = SECRET_KEY
CORS(app)

dynamodb = boto3.resource("dynamodb", region_name=REGION)
s3       = boto3.client("s3", region_name=REGION)

login_table = dynamodb.Table("login")
music_table = dynamodb.Table("music")
sub_table   = dynamodb.Table("subscriptions")

def presigned_url(image_url):
    try:
        filename = image_url.split("/")[-1]
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": f"images/{filename}"},
            ExpiresIn=3600,
        )
    except:
        return image_url

@app.route("/login", methods=["POST"])
def login():
    body     = request.get_json()
    email    = body.get("email", "").strip()
    password = body.get("password", "").strip()
    item = login_table.get_item(Key={"email": email}).get("Item")
    if not item or item["password"] != password:
        return jsonify({"error": "email or password is invalid"}), 401
    return jsonify({"user_name": item["user_name"], "email": email}), 200

@app.route("/register", methods=["POST"])
def register():
    body      = request.get_json()
    email     = body.get("email", "").strip()
    user_name = body.get("user_name", "").strip()
    password  = body.get("password", "").strip()
    if login_table.get_item(Key={"email": email}).get("Item"):
        return jsonify({"error": "The email already exists"}), 409
    login_table.put_item(Item={"email": email, "user_name": user_name, "password": password})
    return jsonify({"message": "Registered successfully"}), 201

@app.route("/logout", methods=["POST"])
def logout():
    return jsonify({"message": "Logged out"}), 200

@app.route("/music/query", methods=["GET"])
def query_music():
    title  = request.args.get("title",  "").strip()
    artist = request.args.get("artist", "").strip()
    year   = request.args.get("year",   "").strip()
    album  = request.args.get("album",  "").strip()

    if not any([title, artist, year, album]):
        return jsonify({"error": "At least one field must be provided"}), 400

    if artist:
        kwargs = {
            "IndexName": "artist-year-index",
            "KeyConditionExpression": Key("artist").eq(artist),
        }
        if year:
            kwargs["KeyConditionExpression"] &= Key("year").eq(year)
        filters = []
        if title: filters.append(Attr("title").eq(title))
        if album: filters.append(Attr("album").eq(album))
        if filters:
            expr = filters[0]
            for f in filters[1:]:
                expr = expr & f
            kwargs["FilterExpression"] = expr
        results = music_table.query(**kwargs).get("Items", [])
    else:
        filters = []
        if title: filters.append(Attr("title").eq(title))
        if year:  filters.append(Attr("year").eq(year))
        if album: filters.append(Attr("album").eq(album))
        expr = filters[0]
        for f in filters[1:]:
            expr = expr & f
        results = music_table.scan(FilterExpression=expr).get("Items", [])

    if not results:
        return jsonify({"message": "No result is retrieved. Please query again", "songs": []}), 200

    for song in results:
        song["presigned_image_url"] = presigned_url(song.get("image_url", ""))

    return jsonify({"songs": results}), 200

@app.route("/subscriptions", methods=["GET"])
def get_subscriptions():
    email = request.args.get("email", "").strip()
    if not email:
        return jsonify({"songs": []}), 200
    items = sub_table.query(
        KeyConditionExpression=Key("email").eq(email)
    ).get("Items", [])
    for item in items:
        item["presigned_image_url"] = presigned_url(item.get("image_url", ""))
    return jsonify({"songs": items}), 200

@app.route("/subscriptions", methods=["POST"])
def subscribe():
    body  = request.get_json()
    email = body.get("email", "").strip()
    if not email:
        return jsonify({"error": "Unauthorised"}), 401
    sub_table.put_item(Item={
        "email":              email,
        "title_artist_album": f"{body['title']}#{body['artist']}#{body['album']}",
        "title":              body["title"],
        "artist":             body["artist"],
        "year":               body.get("year", ""),
        "album":              body["album"],
        "image_url":          body.get("image_url", ""),
    })
    return jsonify({"message": "Subscribed"}), 201

@app.route("/subscriptions", methods=["DELETE"])
def unsubscribe():
    body  = request.get_json()
    email = body.get("email", "").strip()
    if not email:
        return jsonify({"error": "Unauthorised"}), 401
    sub_table.delete_item(Key={
        "email":              email,
        "title_artist_album": f"{body['title']}#{body['artist']}#{body['album']}",
    })
    return jsonify({"message": "Unsubscribed"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)