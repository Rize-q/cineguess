import boto3
import os
from io import BytesIO
from PIL import Image, ImageFilter
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = "cineguess-posters"
ENDPOINT_URL = os.getenv("MINISTACK_ENDPOINT", "http://localhost:4566")

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    )

def blur_image(image_bytes, blur_radius=20):
    """Create a heavily blurred version of the image"""
    img = Image.open(BytesIO(image_bytes))
    img = img.convert("RGB")
    blurred = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    output = BytesIO()
    blurred.save(output, format="JPEG", quality=60)
    return output.getvalue()

def upload_poster(movie_id, image_bytes):
    """Upload both original and blurred poster to S3"""
    s3 = get_s3_client()

    # Upload original poster
    original_key = f"posters/{movie_id}/original.jpg"
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=original_key,
        Body=image_bytes,
        ContentType="image/jpeg"
    )

    # Upload blurred poster
    blurred_bytes = blur_image(image_bytes)
    blurred_key = f"posters/{movie_id}/blurred.jpg"
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=blurred_key,
        Body=blurred_bytes,
        ContentType="image/jpeg"
    )

    return {
        "original_key": original_key,
        "blurred_key": blurred_key
    }

def get_poster(key):
    """Get poster image bytes from S3"""
    s3 = get_s3_client()
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        return response["Body"].read()
    except Exception as e:
        print(f"Error getting poster: {e}")
        return None

def poster_exists(movie_id):
    """Check if poster already exists in S3"""
    s3 = get_s3_client()
    try:
        s3.head_object(Bucket=BUCKET_NAME, Key=f"posters/{movie_id}/original.jpg")
        return True
    except:
        return False