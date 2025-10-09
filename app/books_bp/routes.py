from flask import render_template, request, redirect, url_for, abort, flash
from . import bp
from ..model import Book, Loan 
from flask_login import login_required, current_user
from mongoengine.errors import NotUniqueError, ValidationError
from datetime import date, timedelta

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

def _rand_date_before_today(min_days=10, max_days=20) -> date:
    return date.today() - timedelta(days=Loan.random_days_between(min_days, max_days))

def _rand_date_after(d: date, min_days=10, max_days=20) -> date:
    # cannot be later than today
    proposed = d + timedelta(days=Loan.random_days_between(min_days, max_days))
    return min(proposed, date.today())

@bp.route("/loan/make/<path:title>", methods=["POST", "GET"])
@login_required
def make_loan(title):
    # non-admin only
    if getattr(current_user, "is_admin", False):
        abort(403)

    book = Book.objects(title=title).first()
    if not book:
        abort(404)

    try:
        borrow_date = _rand_date_before_today(10, 20)
        Loan.create_for(user=current_user, book=book, borrow_date=borrow_date)
        flash("Loan created successfully.", "success")
    except ValidationError as e:
        flash(str(e), "warning")

    dest = request.args.get("next") or url_for("books.book_detail", title=title)
    return redirect(dest)

@bp.route("/loans")
@login_required
def loans_list():
    if getattr(current_user, "is_admin", False):
        abort(403)
    loans = Loan.for_user(current_user)
    return render_template(
        "loans.html",
        loans=loans,
        active_page="loans",
        header_class="bg-success-subtle border-bottom border-success",
    )


@bp.route("/loan/<loan_id>/return", methods=["POST"])
@login_required
def loan_return(loan_id):
    if getattr(current_user, "is_admin", False):
        abort(403)
    loan = Loan.by_id_for_user(current_user, loan_id)
    if not loan:
        abort(404)
    try:
        new_return_date = _rand_date_after(loan.borrow_date, 10, 20)
        loan.do_return(new_return_date)
        flash("Book returned.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    return redirect(url_for("books.loans_list"))


@bp.route("/loan/<loan_id>/renew", methods=["POST"])
@login_required
def loan_renew(loan_id):
    if getattr(current_user, "is_admin", False):
        abort(403)
    loan = Loan.by_id_for_user(current_user, loan_id)
    if not loan:
        abort(404)
    try:
        new_borrow_date = _rand_date_after(loan.borrow_date, 10, 20)
        loan.do_renew(new_borrow_date)
        flash("Loan renewed.", "success")
    except ValidationError as e:
        flash(str(e), "warning")
    return redirect(url_for("books.loans_list"))


@bp.route("/loan/<loan_id>/delete", methods=["POST"])
@login_required
def loan_delete(loan_id):
    if getattr(current_user, "is_admin", False):
        abort(403)
    loan = Loan.by_id_for_user(current_user, loan_id)
    if not loan:
        abort(404)
    try:
        loan.delete_if_returned()
        flash("Loan deleted.", "info")
    except ValidationError as e:
        flash(str(e), "warning")
    return redirect(url_for("books.loans_list"))
