from flask import render_template, request, redirect, url_for, abort, flash
from . import bp
from ..model import Book
from flask_login import login_required, current_user
from mongoengine.errors import NotUniqueError, ValidationError

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

@bp.route("/books/new", methods=["GET", "POST"])
@login_required
def new_book():
    if not getattr(current_user, "is_admin", False):
        abort(403)

    
    genres_choices = [
        "Animals","Business","Comics","Communication","Dark Academia","Emotion",
        "Fantasy","Fiction","Friendship","Graphic Novels","Grief","Historical Fiction",
        "Indigenous","Inspirational","Magic","Mental Health","Nonfiction",
        "Personal Development","Philosophy","Picture Books","Poetry","Productivity",
        "Psychology","Romance","School","Self Help"
    ]
    categories = ["Children", "Teens", "Adult"]

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        category = (request.form.get("category") or "").strip()
        url = (request.form.get("url") or "").strip()

        
        genres = request.form.getlist("genres")

        
        raw_desc = (request.form.get("description") or "").strip()
        description = [p.strip() for p in raw_desc.split("\n") if p.strip()]

        
        authors = []
        for i in range(1, 6):
            name = (request.form.get(f"author{i}") or "").strip()
            is_illus = request.form.get(f"author{i}_illus") == "on"
            if name:
                authors.append(f"{name} (Illustrator)" if is_illus else name)

        def _to_int(name):
            v = request.form.get(name, "").strip()
            if not v:
                return None
            try:
                return int(v)
            except ValueError:
                return None

        pages = _to_int("pages")
        copies = _to_int("copies")
        available = _to_int("available")

       
        if not title or category not in categories or not url:
            flash("Please fill in Title, Category, and URL.", "warning")
            return render_template(
                "new_book.html",
                categories=categories,
                genres_choices=genres_choices,
            )

        if copies is not None and available is not None and available > copies:
            flash("'Available' cannot exceed 'Copies'.", "warning")
            return render_template(
                "new_book.html",
                categories=categories,
                genres_choices=genres_choices,
            )

        
        if Book.objects(title=title).first():
            flash("A book with this title already exists.", "danger")
            return render_template(
                "new_book.html",
                categories=categories,
                genres_choices=genres_choices,
            )

        try:
            Book(
                genres=genres,
                title=title,
                category=category,
                url=url,
                description=description,
                authors=authors,
                pages=pages,
                available=available,
                copies=copies,
            ).save()
            flash("New book added successfully.", "success")
            
            return redirect(url_for("books.new_book"))
        except (ValidationError, NotUniqueError) as e:
            flash(f"Could not save: {e}", "danger")

    return render_template(
        "new_book.html",
        categories=categories,
        genres_choices=genres_choices,
    )
