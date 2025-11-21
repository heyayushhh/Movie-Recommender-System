import pickle
from flask import Flask, request, redirect, url_for
from flask import render_template_string
import requests
import numpy as np

app = Flask(__name__)
session = requests.Session()
POSTER_CACHE = {}
RECS_CACHE = {}

def fetch_poster(movie_id):
    if movie_id in POSTER_CACHE:
        return POSTER_CACHE[movie_id]
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key=8265bd1679663a7ea12ac168da84d2e8&language=en-US"
    try:
        r = session.get(url, timeout=(2, 4))
        data = r.json()
        poster_path = data.get('poster_path')
        poster_url = "https://image.tmdb.org/t/p/w500/" + poster_path if poster_path else None
        POSTER_CACHE[movie_id] = poster_url
        return poster_url
    except Exception:
        POSTER_CACHE[movie_id] = None
        return None

def recommend(movie, movies, similarity):
    index = movies[movies['title'] == movie].index[0]
    row = np.asarray(similarity[index])
    top_idx = np.argpartition(row, -6)[-6:]
    top_idx = top_idx[np.argsort(row[top_idx])[::-1]]
    names = []
    posters = []
    for j in top_idx:
        if j == index:
            continue
        movie_id = int(movies.iloc[j].movie_id)
        names.append(movies.iloc[j].title)
        posters.append(fetch_poster(movie_id))
        if len(names) == 5:
            break
    return names, posters

movies = pickle.load(open('model/movie_list.pkl','rb'))
similarity = pickle.load(open('model/similarity.pkl','rb'))

PAGE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Movie Recommender System</title>
    <style>
      :root {
        --bg: #0b0f14;
        --panel: #11161c;
        --text: #e6e6e6;
        --muted: #a0a7b0;
        --accent: #e50914;
        --accent2: #b81d24;
        --card: #0e1318;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        color: var(--text);
        background: radial-gradient(1200px 600px at 10% -10%, #132031 0%, transparent 40%),
                    radial-gradient(1000px 500px at 90% -20%, #1b0f15 0%, transparent 40%),
                    var(--bg);
        font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      }
      .container { max-width: 1200px; margin: 0 auto; padding: 28px; }
      .header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 18px; }
      .title { font-size: 28px; font-weight: 800; letter-spacing: 0.5px; }
      .subtitle { color: var(--muted); font-size: 14px; }
      .panel { background: linear-gradient(180deg, rgba(17,22,28,0.9), rgba(17,22,28,0.6)); border: 1px solid #1f2630; border-radius: 14px; padding: 18px; backdrop-filter: blur(6px); }
      .form { display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: center; }
      label { color: var(--muted); font-size: 13px; margin-bottom: 6px; display: block; }
      select { width: 100%; padding: 12px 14px; border-radius: 10px; background: #0f141a; color: var(--text); border: 1px solid #202733; outline: none; }
      select:focus { border-color: #2d3748; box-shadow: 0 0 0 2px rgba(229,9,20,0.15); }
      button { padding: 12px 16px; border: none; border-radius: 10px; color: #fff; font-weight: 600; background: linear-gradient(135deg, var(--accent), var(--accent2)); cursor: pointer; }
      button:hover { filter: brightness(1.05); }
      .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 18px; margin-top: 22px; }
      .card { background: var(--card); border: 1px solid #1b222b; border-radius: 16px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.35); transition: transform 160ms ease, box-shadow 160ms ease; }
      .card:hover { transform: translateY(-4px); box-shadow: 0 14px 32px rgba(0,0,0,0.45); }
      .poster { aspect-ratio: 2/3; width: 100%; display: block; }
      .placeholder { aspect-ratio: 2/3; width: 100%; background: linear-gradient(180deg, #12171d, #0c1015); display: grid; place-items: center; color: var(--muted); font-size: 12px; }
      .name { padding: 12px 12px 14px; font-weight: 700; font-size: 14px; text-align: center; }
      .footer { color: var(--muted); font-size: 12px; text-align: center; margin-top: 26px; }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="header">
        <div class="title">Movie Recommender</div>
        <div class="subtitle">Discover 5 similar titles instantly</div>
      </div>
      <div class="panel">
        <form class="form" method="post" action="/">
          <div>
            <label for="movie">Select a movie</label>
            <select name="movie" id="movie">
              {% for m in movie_list %}
              <option value="{{ m }}" {% if selected == m %}selected{% endif %}>{{ m }}</option>
              {% endfor %}
            </select>
          </div>
          <div>
            <button type="submit">Show Recommendation</button>
          </div>
        </form>
        {% if names %}
        <div class="grid">
          {% for n, p in items %}
          <div class="card">
            {% if p %}
            <img class="poster" src="{{ p }}" alt="{{ n }} poster" />
            {% else %}
            <div class="placeholder">No image</div>
            {% endif %}
            <div class="name">{{ n }}</div>
          </div>
          {% endfor %}
        </div>
        {% endif %}
      </div>
      <div class="footer">Powered by TMDB</div>
    </div>
  </body>
  </html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    selected = None
    names = []
    posters = []
    if request.method == 'POST':
        selected = request.form.get('movie')
        if selected:
            cached = RECS_CACHE.get(selected)
            if cached:
                names, posters = cached
            else:
                names, posters = recommend(selected, movies, similarity)
                RECS_CACHE[selected] = (names, posters)
    items = list(zip(names, posters))
    return render_template_string(PAGE, movie_list=movies['title'].values, selected=selected, names=names, items=items)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=False)