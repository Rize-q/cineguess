import boto3
import requests
import os
import time
from decimal import Decimal
from io import BytesIO
from PIL import Image, ImageFilter
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
MINISTACK_ENDPOINT = os.getenv("MINISTACK_ENDPOINT", "http://localhost:4566")
BUCKET_NAME = "cineguess-posters"

AWS_ARGS = {
    "endpoint_url": MINISTACK_ENDPOINT,
    "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID", "test"),
    "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    "region_name": os.getenv("AWS_DEFAULT_REGION", "us-east-1")
}

# ── Daftar Film (tambah/kurangi sesukamu) ─────────────────
# Format: TMDB movie ID
# Cari ID film di: https://www.themoviedb.org/movie/<ID>

MOVIE_IDS = [
    27205,    # Inception (2010)
    157336,   # Interstellar (2014)
    155,      # The Dark Knight (2008)
    603,      # The Matrix (1999)
    13,       # Forrest Gump (1994)
    238,      # The Godfather (1972)
    424,      # Schindler's List (1993)
    550,      # Fight Club (1999)
    1233413,  # Sinners (2025)
    1244492,  # Look Back (2024)
    38,       # Eternal Sunshine of the Spotless Mind (2004)
    24428,    # The Avengers (2012)
    274,      # The Silence of the Lambs (1991)
    120,      # The Lord of the Rings: The Fellowship
    1074313,  # Jatuh Cinta Seperti di Film-Film (2023)
    1393326,  # Ghost in the Cell (2026)
    372058,   # Kimi no Na wa (2016)
    38142,    # 5 Centimeters per Second (2007)
]

# Filter hanya integer IDs yang valid
MOVIE_IDS = [mid for mid in MOVIE_IDS if isinstance(mid, int)]

# ── Helpers ───────────────────────────────────────────────

def get_tmdb(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    res = requests.get(url, params={
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "append_to_response": "credits"
    })
    return res.json()

def extract_clues(detail):
    genres = [g["name"] for g in detail.get("genres", [])]
    cast = detail.get("credits", {}).get("cast", [])
    actors = [c["name"] for c in cast[:3]]
    synopsis = detail.get("overview", "")
    words = synopsis.split()
    vague = " ".join(words[:20]) + "..." if len(words) > 20 else synopsis
    return {
        "genre": ", ".join(genres) if genres else "Unknown",
        "year": detail.get("release_date", "")[:4],
        "actors": ", ".join(actors) if actors else "Unknown",
        "synopsis": vague,
        "rating": Decimal(str(round(detail.get("vote_average", 0), 1)))
    }

def blur_image(image_bytes, radius=20):
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    blurred = img.filter(ImageFilter.GaussianBlur(radius=radius))
    out = BytesIO()
    blurred.save(out, format="JPEG", quality=60)
    return out.getvalue()

def upload_poster(s3, movie_id, image_bytes):
    s3.put_object(Bucket=BUCKET_NAME, Key=f"posters/{movie_id}/original.jpg",
                  Body=image_bytes, ContentType="image/jpeg")
    s3.put_object(Bucket=BUCKET_NAME, Key=f"posters/{movie_id}/blurred.jpg",
                  Body=blur_image(image_bytes), ContentType="image/jpeg")

def poster_exists(s3, movie_id):
    try:
        s3.head_object(Bucket=BUCKET_NAME, Key=f"posters/{movie_id}/original.jpg")
        return True
    except:
        return False

def movie_exists(table, movie_id):
    res = table.get_item(Key={"movie_id": str(movie_id)})
    return "Item" in res

# ── Main ──────────────────────────────────────────────────

def main():
    print("\n🎬 CineGuess — Add Initial Movie")
    print("=" * 40)

    s3 = boto3.client("s3", **AWS_ARGS)
    db = boto3.resource("dynamodb", **AWS_ARGS)
    table = db.Table("Movies")

    success = 0
    skipped = 0
    failed = 0

    for movie_id in MOVIE_IDS:
        # Skip jika sudah ada di database
        if movie_exists(table, movie_id):
            print(f"⏭️  Skipping (already exists): ID {movie_id}")
            skipped += 1
            continue

        try:
            # Fetch dari TMDB
            detail = get_tmdb(movie_id)
            title = detail.get("title", "Unknown")

            if not detail.get("id"):
                print(f"❌ Not found on TMDB: ID {movie_id}")
                failed += 1
                continue

            print(f"⬇️  Fetching: {title}...", end=" ")

            # Upload poster ke S3
            poster_path = detail.get("poster_path")
            has_poster = False
            if poster_path and not poster_exists(s3, movie_id):
                img_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
                img_res = requests.get(img_url)
                if img_res.status_code == 200:
                    upload_poster(s3, movie_id, img_res.content)
                    has_poster = True

            # Simpan ke DynamoDB
            clues = extract_clues(detail)
            table.put_item(Item={
                "movie_id": str(movie_id),
                "title": title,
                "clues": clues,
                "has_poster": has_poster,
                "is_daily": False
            })

            print(f"✅ Done")
            success += 1
            time.sleep(0.3)  # hindari rate limit TMDB

        except Exception as e:
            print(f"❌ Error: {e}")
            failed += 1

    print("\n" + "=" * 40)
    print(f"✅ Added  : {success} movies")
    print(f"⏭️  Skipped: {skipped} movies (already in DB)")
    print(f"❌ Failed : {failed} movies")
    print("=" * 40)
    print("🚀 Run 'python app.py' to start the game!\n")

if __name__ == "__main__":
    main()