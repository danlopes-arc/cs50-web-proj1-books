import os
import requests

from flask import Flask, session, redirect, render_template, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from sqlalchemy.orm import scoped_session, sessionmaker
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

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

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

@app.route("/", methods=["GET", "POST"])
def index():
    books = db.execute("SELECT * FROM books;")
    term = request.form.get("term")

    if request.method == "GET" or not term:
        return render_template("index.html", books=books)

    filtered_books = []
    col_names = ["isbn", "title", "author"]
    for book in books:
        for col_name in col_names:
            if book[col_name].lower().find(term.lower()) >= 0:
                filtered_books.append(book)
                break
    
    return render_template("index.html", books=filtered_books, term=term)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    
    nickname = request.form.get("nickname")
    password = request.form.get("password")
    rpassword = request.form.get("repeat-password")

    errors = []
    if len(nickname) == 0:
        errors.append("Nickname is empty")
    if len(password) == 0:
        errors.append("Password is empty")
    elif password != rpassword:
        errors.append("Passwords don't match")

    if len(errors) == 0:
        user = db.execute(text("SELECT * FROM users WHERE nickname = :nickname;"),{"nickname": nickname}).fetchall()
        if user:
            errors.append("This nickname already exists")
    
    if errors:
        return render_template("signup.html", errors=errors)
    
    hash = generate_password_hash(password)
    db.execute(text("INSERT INTO users(nickname, hash) VALUES(:nickname, :hash);"), {"nickname": nickname, "hash": hash})

    return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "GET":
        return render_template("login.html")

    nickname = request.form.get("nickname")
    password = request.form.get("password")

    errors = []
    if len(nickname) == 0:
        errors.append("Nickname is empty")
    if len(password) == 0:
        errors.append("Password is empty")

    if not errors:
        user_query = db.execute(text("SELECT * FROM users WHERE nickname = :nickname;"),{"nickname": nickname})

        user = query_to_dict_array(user_query)
        if not user:
            errors.append("User doesn't exist")
        else:
            user = user[0]

            if not check_password_hash(user["hash"], password):
                errors.append("Wrong password")
    
    if errors:
        return render_template("login.html", errors=errors)

    session["user_id"] = user["id"]

    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/<isbn>", methods=["GET", "POST"])
def book(isbn):
    book_q = db.execute(text("SELECT * FROM books WHERE isbn = :isbn;"), {"isbn": isbn})
    book = query_to_dict_array(book_q)
    if not book:
        return render_template("book.html")
    book = book[0]

    user_id = session.get("user_id")

    review_q = db.execute(text("""
    SELECT * FROM reviews
    WHERE user_id = :user_id
    AND book_id = (
        SELECT id FROM books WHERE isbn = :isbn
    );
    """), {"user_id": user_id, "isbn": isbn})
    review = query_to_dict_array(review_q)

    has_reviewed = bool(review)
    if has_reviewed:
        review = review[0]

    reviews_q = db.execute(text("""
    SELECT * FROM reviews
    JOIN users
    ON reviews.user_id = users.id
    WHERE reviews.book_id = (
        SELECT id FROM books WHERE isbn = :isbn
    );
    """), {"isbn": isbn})
    reviews = query_to_dict_array(reviews_q)

    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": GOODREADS_KEY, "isbns": isbn})

    goodreads_info = res.json()["books"][0]

    if request.method == "GET":
        return render_template("book.html", book=book, reviews=reviews, user_review=review, goodreads_info=goodreads_info)

    rev_text = request.form.get("text")
    rating = int(request.form.get("rating"))

    errors = []
    if not rev_text:
        errors.append("Review text is empty")

    if has_reviewed:
        errors.append("You've already posted a review about this book")
    
    if errors:
        return render_template("book.html", book=book, reviews=reviews, errors=errors, user_review=review, goodreads_info=goodreads_info)

    db.execute(text("""
    INSERT INTO reviews(user_id, book_id, rating, text)
    VALUES(:user_id, :book_id, :rating, :text);
    """), {"user_id": user_id, "book_id": book["id"], "rating": rating, "text": rev_text})

    return redirect("/" + isbn)


def query_to_dict_array(query):
    d, a = {}, []
    for row in query:
        for col, value in row.items():
            d = {**d, **{col: value}}
        a.append(d)
    return a