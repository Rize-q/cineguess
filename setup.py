import boto3
import os
import time
from dotenv import load_dotenv

load_dotenv()

client_args = {
    "endpoint_url": os.getenv("MINISTACK_ENDPOINT", "http://localhost:4566"),
    "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID", "test"),
    "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    "region_name": os.getenv("AWS_DEFAULT_REGION", "us-east-1")
}

def setup_s3():
    s3 = boto3.client("s3", **client_args)
    try:
        s3.create_bucket(Bucket="cineguess-posters")
        print("✅ S3 bucket 'cineguess-posters' created")
    except Exception as e:
        if "BucketAlreadyOwnedByYou" in str(e) or "BucketAlreadyExists" in str(e):
            print("✅ S3 bucket already exists")
        else:
            print(f"❌ S3 error: {e}")

def setup_dynamodb():
    db = boto3.client("dynamodb", **client_args)
    tables = [
        ("Movies", "movie_id"),
        ("Scores", "player_id")
    ]
    for table_name, key in tables:
        try:
            db.create_table(
                TableName=table_name,
                AttributeDefinitions=[{"AttributeName": key, "AttributeType": "S"}],
                KeySchema=[{"AttributeName": key, "KeyType": "HASH"}],
                BillingMode="PAY_PER_REQUEST"
            )
            print(f"✅ DynamoDB table '{table_name}' created")
        except Exception as e:
            if "ResourceInUseException" in str(e):
                print(f"✅ DynamoDB table '{table_name}' already exists")
            else:
                print(f"❌ DynamoDB error: {e}")

def check_ministack():
    import requests
    try:
        res = requests.get("http://localhost:4566/_ministack/health", timeout=3)
        if res.status_code == 200:
            return True
    except:
        pass
    return False

if __name__ == "__main__":
    print("\n🎬 CineGuess — Setup")
    print("=" * 35)

    print("\n⏳ Checking MiniStack connection...")
    for i in range(5):
        if check_ministack():
            print("✅ MiniStack is running!")
            break
        print(f"   Retrying... ({i+1}/5)")
        time.sleep(2)
    else:
        print("❌ Cannot connect to MiniStack!")
        print("   Make sure Docker + MiniStack is running first.")
        print("   Command: docker run -p 4566:4566 ministackorg/ministack")
        exit(1)

    print("\n📦 Setting up S3...")
    setup_s3()

    print("\n🗄️  Setting up DynamoDB...")
    setup_dynamodb()

    print("\n✨ Setup complete!")
    print("=" * 35 + "\n")