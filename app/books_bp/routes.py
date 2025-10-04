from flask import render_template, request, redirect, url_for, abort
from . import bp
from ..model import Book

@bp.route("/")
def home():
    return redirect(url_for("books.book_titles"))

@bp.route("/books")
def book_titles():
    selected = request.args.get("category", "All")

    qs = Book.objects
    if selected != "All":
        qs = qs.filter(category=selected)

    books = list(qs.order_by("+title"))
    categories = ["All"] + sorted({b.category for b in Book.objects.only("category")})

    return render_template(
        "list.html",
        books=books,
        categories=categories,
        selected=selected,
        active_page="books",
        current_year=2025,
    )

@bp.route("/book/<path:title>")
def book_detail(title):
    book = Book.objects(title=title).first()
    if not book:
        abort(404)
    
    return render_template(
        "detail.html",
        b=book,
        active_page="books",
        current_year=2025,
    )
