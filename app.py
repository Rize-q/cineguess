from flask import Flask, render_template, request, jsonify, send_file
from io import BytesIO
import random
from services.tmdb import search_movies, get_movie_detail, download_poster, extract_clues
from services.s3_storage import upload_poster, get_poster, poster_exists
from services.dynamodb import (
    save_movie, get_movie, get_all_movies,
    get_daily_movie, set_daily_movie,
    save_score, get_leaderboard
)

app = Flask(__name__)

# ── Helpers ───────────────────────────────────────────────

def pick_random_movie():
    """Pick a random movie from the pool and set it as active"""
    movies = get_all_movies()
    if not movies:
        return None
    chosen = random.choice(movies)
    set_daily_movie(chosen["movie_id"])
    return get_daily_movie()  # re-fetch so _fix_decimals runs

def ensure_active_movie():
    """Get current active movie, auto-pick one if none is set"""
    current = get_daily_movie()
    if not current:
        current = pick_random_movie()
    return current

# ── Pages ─────────────────────────────────────────────────

@app.route("/")
def index():
    movies = get_all_movies()
    daily = get_daily_movie()
    return render_template("index.html", movies=movies, daily=daily)

@app.route("/game")
def game():
    daily = ensure_active_movie()
    if not daily:
        return render_template("index.html", error="No movies in database yet! Add at least one movie first.", movies=[], daily=None)
    return render_template("game.html", movie=daily)

# ── API: Search & Add Movie ───────────────────────────────

@app.route("/api/search")
def api_search():
    query = request.args.get("q", "")
    if not query:
        return jsonify([])
    results = search_movies(query)
    simplified = [{
        "id": m["id"],
        "title": m["title"],
        "year": m.get("release_date", "")[:4],
        "poster_path": m.get("poster_path")
    } for m in results[:8]]
    return jsonify(simplified)

@app.route("/api/add-movie", methods=["POST"])
def api_add_movie():
    data = request.json
    movie_id = str(data.get("movie_id"))

    existing = get_movie(movie_id)
    if existing:
        return jsonify({"success": False, "message": "Movie already added!"})

    detail = get_movie_detail(movie_id)
    clues = extract_clues(detail)
    poster_path = detail.get("poster_path")

    if poster_path and not poster_exists(movie_id):
        image_bytes = download_poster(poster_path)
        if image_bytes:
            upload_poster(movie_id, image_bytes)

    movie_data = {
        "movie_id": movie_id,
        "title": detail.get("title", "Unknown"),
        "clues": clues,
        "has_poster": poster_path is not None,
        "is_daily": False
    }
    save_movie(movie_data)

    return jsonify({"success": True, "message": f"'{detail['title']}' added successfully!"})

# ── API: Poster Serving ───────────────────────────────────

@app.route("/poster/<movie_id>/<version>")
def serve_poster(movie_id, version):
    key = f"posters/{movie_id}/{version}.jpg"
    image_bytes = get_poster(key)
    if not image_bytes:
        return "Poster not found", 404
    return send_file(BytesIO(image_bytes), mimetype="image/jpeg")

# ── API: Submit Guess ─────────────────────────────────────

@app.route("/api/guess", methods=["POST"])
def api_guess():
    data = request.json
    player_name = data.get("player_name", "Anonymous")
    guess = data.get("guess", "").strip().lower()
    clues_used = int(data.get("clues_used", 1))

    daily = get_daily_movie()
    if not daily:
        return jsonify({"correct": False, "message": "No active movie!"})

    correct_title = daily["title"].strip().lower()
    is_correct = guess == correct_title
    game_over = is_correct or clues_used >= 6

    if game_over:
        save_score(player_name, daily["movie_id"], clues_used, is_correct)

    # Auto-pick next random movie when correctly guessed
    if is_correct:
        pick_random_movie()

    return jsonify({
        "correct": is_correct,
        "answer": daily["title"] if (not is_correct and clues_used >= 6) else None,
        "score": max(0, (6 - clues_used) * 100) if is_correct else 0
    })

# ── API: Skip / Force New Random Movie ───────────────────

@app.route("/api/skip-movie", methods=["POST"])
def api_skip_movie():
    next_movie = pick_random_movie()
    if not next_movie:
        return jsonify({"success": False, "message": "No movies available!"})
    return jsonify({"success": True, "message": f"Now playing: '{next_movie['title']}'"})

# ── API: Leaderboard ──────────────────────────────────────

@app.route("/api/leaderboard")
def api_leaderboard():
    scores = get_leaderboard()
    for s in scores:
        s["score"] = int(s["score"])
        s["clues_used"] = int(s["clues_used"])
    return jsonify(scores)

# ── Run ───────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)