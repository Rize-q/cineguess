import boto3
import os
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

ENDPOINT_URL = os.getenv("MINISTACK_ENDPOINT", "http://localhost:4566")

def get_dynamodb():
    return boto3.resource(
        "dynamodb",
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    )

def _fix_decimals(item):
    """Convert Decimal values to string/int for safe usage"""
    if item and "clues" in item:
        clues = item["clues"]
        if "rating" in clues:
            clues["rating"] = str(clues["rating"])
    return item

# ── Movies ──────────────────────────────────────────────

def save_movie(movie_data):
    """Save movie to DynamoDB"""
    db = get_dynamodb()
    table = db.Table("Movies")
    table.put_item(Item=movie_data)

def get_movie(movie_id):
    """Get movie by ID"""
    db = get_dynamodb()
    table = db.Table("Movies")
    response = table.get_item(Key={"movie_id": str(movie_id)})
    return _fix_decimals(response.get("Item"))

def get_all_movies():
    """Get all movies from DynamoDB"""
    db = get_dynamodb()
    table = db.Table("Movies")
    response = table.scan()
    return [_fix_decimals(item) for item in response.get("Items", [])]

def get_daily_movie():
    """Get the current daily challenge movie"""
    db = get_dynamodb()
    table = db.Table("Movies")
    response = table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("is_daily").eq(True)
    )
    items = response.get("Items", [])
    return _fix_decimals(items[0]) if items else None

def set_daily_movie(movie_id):
    """Set a movie as the daily challenge (reset others first)"""
    db = get_dynamodb()
    table = db.Table("Movies")

    # Reset all daily flags
    all_movies = get_all_movies()
    for movie in all_movies:
        if movie.get("is_daily"):
            table.update_item(
                Key={"movie_id": movie["movie_id"]},
                UpdateExpression="SET is_daily = :val",
                ExpressionAttributeValues={":val": False}
            )

    # Set new daily movie
    table.update_item(
        Key={"movie_id": str(movie_id)},
        UpdateExpression="SET is_daily = :val",
        ExpressionAttributeValues={":val": True}
    )

# ── Scores ───────────────────────────────────────────────

def save_score(player_name, movie_id, clues_used, won):
    """Save a player's game result"""
    import time
    db = get_dynamodb()
    table = db.Table("Scores")

    score = max(0, (6 - clues_used) * 100) if won else 0

    entry = {
        "player_id": f"{player_name}#{int(time.time())}",
        "player_name": player_name,
        "movie_id": str(movie_id),
        "clues_used": clues_used,
        "won": won,
        "score": score,
        "timestamp": int(time.time())
    }
    table.put_item(Item=entry)
    return entry

def get_leaderboard():
    """Get top 10 scores"""
    db = get_dynamodb()
    table = db.Table("Scores")
    response = table.scan()
    items = response.get("Items", [])
    sorted_items = sorted(items, key=lambda x: int(x.get("score", 0)), reverse=True)
    return sorted_items[:10]