import json
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr

REGION    = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET = os.environ.get("S3_BUCKET",  "taniya-music-app-2026")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
s3       = boto3.client("s3", region_name=REGION)

login_table = dynamodb.Table("login")
music_table = dynamodb.Table("music")
sub_table   = dynamodb.Table("subscriptions")

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
}

def respond(status_code, body):
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, default=str),
    }

def get_body(event):
    raw = event.get("body", "{}")
    if not raw:
        return {}
    return json.loads(raw) if isinstance(raw, str) else raw

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

def lambda_handler(event, context):
    method   = event.get("httpMethod", "GET")
    resource = event.get("resource", "/")

    if method == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    if resource == "/login" and method == "POST":
        return handle_login(event)
    elif resource == "/register" and method == "POST":
        return handle_register(event)
    elif resource == "/logout" and method == "POST":
        return respond(200, {"message": "Logged out"})
    elif resource == "/music/query" and method == "GET":
        return handle_query(event)
    elif resource == "/subscriptions" and method == "GET":
        return handle_get_subs(event)
    elif resource == "/subscriptions" and method == "POST":
        return handle_subscribe(event)
    elif resource == "/subscriptions" and method == "DELETE":
        return handle_unsubscribe(event)
    else:
        return respond(404, {"error": f"Route not found: {method} {resource}"})

def handle_login(event):
    body     = get_body(event)
    email    = body.get("email", "").strip()
    password = body.get("password", "").strip()
    item = login_table.get_item(Key={"email": email}).get("Item")
    if not item or item["password"] != password:
        return respond(401, {"error": "email or password is invalid"})
    return respond(200, {"user_name": item["user_name"], "email": email})

def handle_register(event):
    body      = get_body(event)
    email     = body.get("email", "").strip()
    user_name = body.get("user_name", "").strip()
    password  = body.get("password", "").strip()
    if login_table.get_item(Key={"email": email}).get("Item"):
        return respond(409, {"error": "The email already exists"})
    login_table.put_item(Item={"email": email, "user_name": user_name, "password": password})
    return respond(201, {"message": "Registered successfully"})

def handle_query(event):
    params = event.get("queryStringParameters") or {}
    title  = params.get("title",  "").strip()
    artist = params.get("artist", "").strip()
    year   = params.get("year",   "").strip()
    album  = params.get("album",  "").strip()

    if not any([title, artist, year, album]):
        return respond(400, {"error": "At least one field must be provided"})

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
        return respond(200, {"message": "No result is retrieved. Please query again", "songs": []})

    for song in results:
        song["presigned_image_url"] = presigned_url(song.get("image_url", ""))

    return respond(200, {"songs": results})

def handle_get_subs(event):
    params = event.get("queryStringParameters") or {}
    email  = params.get("email", "").strip()
    if not email:
        return respond(200, {"songs": []})
    items = sub_table.query(
        KeyConditionExpression=Key("email").eq(email)
    ).get("Items", [])
    for item in items:
        item["presigned_image_url"] = presigned_url(item.get("image_url", ""))
    return respond(200, {"songs": items})

def handle_subscribe(event):
    body  = get_body(event)
    email = body.get("email", "").strip()
    if not email:
        return respond(401, {"error": "Unauthorised"})
    sub_table.put_item(Item={
        "email":              email,
        "title_artist_album": f"{body['title']}#{body['artist']}#{body['album']}",
        "title":              body["title"],
        "artist":             body["artist"],
        "year":               body.get("year", ""),
        "album":              body["album"],
        "image_url":          body.get("image_url", ""),
    })
    return respond(201, {"message": "Subscribed"})

def handle_unsubscribe(event):
    body  = get_body(event)
    email = body.get("email", "").strip()
    if not email:
        return respond(401, {"error": "Unauthorised"})
    sub_table.delete_item(Key={
        "email":              email,
        "title_artist_album": f"{body['title']}#{body['artist']}#{body['album']}",
    })
    return respond(200, {"message": "Unsubscribed"})
