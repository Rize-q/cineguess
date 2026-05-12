import requests
import os
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

def search_movies(query):
    """Search movies by title from TMDB"""
    url = f"{BASE_URL}/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
        "language": "en-US",
        "page": 1
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data.get("results", [])

def get_movie_detail(movie_id):
    """Get detailed movie info including credits"""
    url = f"{BASE_URL}/movie/{movie_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "append_to_response": "credits"
    }
    response = requests.get(url, params=params)
    return response.json()

def get_poster_url(poster_path):
    """Get full poster URL from poster path"""
    if poster_path:
        return f"{IMAGE_BASE_URL}{poster_path}"
    return None

def download_poster(poster_path):
    """Download poster image as bytes"""
    url = get_poster_url(poster_path)
    if not url:
        return None
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    return None

def get_popular_movies(page=1):
    """Get list of popular movies"""
    url = f"{BASE_URL}/movie/popular"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "page": page
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data.get("results", [])

def extract_clues(movie_detail):
    """Extract clue data from movie detail"""
    genres = [g["name"] for g in movie_detail.get("genres", [])]
    
    cast = movie_detail.get("credits", {}).get("cast", [])
    top_actors = [c["name"] for c in cast[:3]]
    
    synopsis = movie_detail.get("overview", "")
    words = synopsis.split()
    vague_synopsis = " ".join(words[:20]) + "..." if len(words) > 20 else synopsis

    return {
        "genre": ", ".join(genres) if genres else "Unknown",
        "year": movie_detail.get("release_date", "")[:4],
        "actors": ", ".join(top_actors) if top_actors else "Unknown",
        "synopsis": vague_synopsis,
        "rating": Decimal(str(round(movie_detail.get("vote_average", 0), 1)))
    }