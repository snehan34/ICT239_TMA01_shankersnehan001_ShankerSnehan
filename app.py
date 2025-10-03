from flask import Flask, render_template, request, redirect, url_for, abort
from books import all_books

app = Flask(__name__)

@app.route("/")
def home():
    return redirect(url_for("book_titles"))

@app.route("/books")
def book_titles():
    selected = request.args.get("category", "All")
    books = [b for b in all_books if selected in ("All", b.get("category"))]
    books = sorted(books, key=lambda b: (b.get("title") or "").lower())
    categories = ["All"] + sorted({(b.get("category") or "").strip() for b in all_books if b.get("category")})
    return render_template("list.html",
                           books=books, categories=categories, selected=selected,
                           active_page="books", current_year=2025)

@app.route("/book/<path:title>")
def book_detail(title):
    book = next((b for b in all_books if b.get("title") == title), None)
    if not book: abort(404)
    return render_template("detail.html", b=book, active_page="books", current_year=2025)


