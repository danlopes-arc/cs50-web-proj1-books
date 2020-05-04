import os
import requests

from flask import Flask, session, redirect, render_template, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from sqlalchemy.orm import scoped_session, sessionmaker
from tempfile import mkdtemp

DATABASE_URL = "postgres://wrsgwrmkrvjnkg:315f2ff023c1d9b3d063fbd2c8c0ec20fe50daae75d8c89525821bfc7c088ffb@ec2-54-88-130-244.compute-1.amazonaws.com:5432/dde9dia2t0hl7o"
GOODREADS_KEY = "9gRUykfyjGUMc0qT9sRrjw"

app = Flask(__name__)

# Check for environment variable
# if not os.getenv("DATABASE_URL"):
#     raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
# engine = create_engine(os.getenv("DATABASE_URL"))
engine = create_engine(DATABASE_URL)
# db = scoped_session(sessionmaker(bind=engine))
db = engine.connect()


@app.route("/", methods=["GET", "POST"])
def index():
    # res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": GOODREADS_KEY, "isbns": "9781632168146"})
    books = db.execute("SELECT * FROM books;")
    session["user_id"] = 12

    if request.method == "GET":
        print(books)
        return render_template("index.html", books=books)

    term = request.form.get("term")

    if not term:
        return render_template("index.html", books=books)

    filtered_books = []
    for book in books:
        if (book["isbn"].lower().find(term.lower()) >= 0 or
            book["title"].lower().find(term.lower()) >= 0 or
            book["author"].lower().find(term.lower()) >= 0):
            filtered_books.append(book)
    
    return render_template("index.html", books=filtered_books, term=term)


