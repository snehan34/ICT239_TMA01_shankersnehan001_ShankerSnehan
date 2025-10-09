from mongoengine import (
    Document, StringField, IntField, ListField, URLField, BooleanField, EmailField
)
from mongoengine import ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Dict, Any, Iterable
from books import all_books 
from mongoengine import DateField, ReferenceField, CASCADE
from datetime import date, timedelta
import random 

class Book(Document):
    meta = {"collection": "books", "indexes": ["title", "category"], "strict": False}
    genres      = ListField(StringField(), default=list)
    title       = StringField(required=True, unique=True)
    category    = StringField(required=True, choices=("Children", "Teens", "Adult"))
    url         = URLField(required=True)
    description = ListField(StringField(), default=list)
    authors     = ListField(StringField(), default=list)
    pages       = IntField(min_value=1)
    available   = IntField(min_value=0)
    copies      = IntField(min_value=0)

    def clean(self):
        if self.available is not None and self.copies is not None:
            if self.available > self.copies:
                raise ValidationError("'available' cannot exceed 'copies'.")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        return cls(
            genres=d.get("genres", []),
            title=d.get("title"),
            category=d.get("category"),
            url=d.get("url"),
            description=d.get("description", []),
            authors=d.get("authors", []),
            pages=d.get("pages"),
            available=d.get("available"),
            copies=d.get("copies"),
        )

    @classmethod
    def seed_many(cls, items: Iterable[Dict[str, Any]]) -> int:
        count = 0
        for raw in items:
            doc = cls.from_dict(raw)
            cls.objects(title=doc.title).modify(
                upsert=True, new=True,
                set__genres=doc.genres, set__category=doc.category, set__url=doc.url,
                set__description=doc.description, set__authors=doc.authors,
                set__pages=doc.pages, set__available=doc.available, set__copies=doc.copies,
            )
            count += 1
        return count
    
    def can_borrow(self) -> bool:
        """True if at least one copy can be loaned out."""
        return (self.available or 0) > 0

    def can_return(self) -> bool:
        """True if a copy can be returned without exceeding 'copies'."""
        a = self.available or 0
        c = self.copies or 0
        return a < c

    def borrow_one(self):
        """
        Decrease available by 1 if possible.
        Raises ValidationError if no copies are available.
        """
        if not self.can_borrow():
            raise ValidationError("No available copies to borrow.")
        self.available = (self.available or 0) - 1
        self.save(validate=True)

    def return_one(self):
        """
        Increase available by 1 if it will not exceed copies.
        Raises ValidationError if it would exceed total copies.
        """
        if not self.can_return():
            raise ValidationError("Cannot return: already at maximum available.")
        self.available = (self.available or 0) + 1
        self.save(validate=True)

def seed_books_if_empty():
    if Book.objects.first() is None:
        Book.seed_many(all_books)


class User(Document):
    meta = {"collection": "users", "indexes": ["email"], "strict": False}
    email    = EmailField(required=True, unique=True)
    password = StringField(required=True)  
    name     = StringField(required=True)
    is_admin = BooleanField(default=False)

    
    @property
    def is_authenticated(self): return True
    @property
    def is_active(self): return True
    @property
    def is_anonymous(self): return False
    def get_id(self): return str(self.id)

    @staticmethod
    def hash_pw(raw): return generate_password_hash(raw)
    def check_pw(self, raw): return check_password_hash(self.password, raw)

def seed_users_if_missing():
    # Admin
    admin = User.objects(email="admin@lib.sg").first()
    if not admin:
        User(email="admin@lib.sg",
             password=User.hash_pw("12345"),
             name="Admin",
             is_admin=True).save()
    # Non-admin
    user = User.objects(email="poh@lib.sg").first()
    if not user:
        User(email="poh@lib.sg",
             password=User.hash_pw("12345"),
             name="Peter Oh",
             is_admin=False).save()

class Loan(Document):
    meta = {
        "collection": "loans",
        "indexes": ["user", ("user", "book", "return_date"), "-borrow_date"],
        "strict": False,
    }

    user        = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    book        = ReferenceField(Book, required=True, reverse_delete_rule=CASCADE)
    borrow_date = DateField(required=True)
    return_date = DateField()
    renew_count = IntField(min_value=0, default=0)

    @property
    def is_returned(self) -> bool:
        return self.return_date is not None

    @property
    def due_date(self) -> date:
        return self.borrow_date + timedelta(days=14)

    @property
    def is_overdue(self) -> bool:
        return (not self.is_returned) and (date.today() > self.due_date)

    @classmethod
    def for_user(cls, user):
        return cls.objects(user=user).order_by("-borrow_date", "-id")

    @classmethod
    def by_id_for_user(cls, user, loan_id):
        return cls.objects(id=loan_id, user=user).first()

    @classmethod
    def create_for(cls, *, user: User, book: Book, borrow_date: date):
        if (book.available or 0) <= 0:
            raise ValidationError("No available copies for this title.")
        if cls.objects(user=user, book=book, return_date=None).first():
            raise ValidationError("You already have an unreturned loan for this title.")

        
        book.available = (book.available or 0) - 1
        book.save(validate=True)

        return cls(user=user, book=book, borrow_date=borrow_date).save()

    
    def can_renew(self) -> bool:
        return (not self.is_returned) and (not self.is_overdue) and (self.renew_count < 2)

    def do_renew(self, new_borrow_date: date):
        if not self.can_renew():
            raise ValidationError("This loan cannot be renewed.")
        self.borrow_date = new_borrow_date
        self.renew_count = (self.renew_count or 0) + 1
        self.save(validate=True)

    def do_return(self, return_date_: date):
        if self.is_returned:
            raise ValidationError("Loan already returned.")
        
        if not self.book.can_return():
            raise ValidationError("Cannot return: already at maximum available.")
        self.book.available = (self.book.available or 0) + 1
        self.book.save(validate=True)

        self.return_date = return_date_
        self.save(validate=True)

    
    def delete_if_returned(self):
        if not self.is_returned:
            raise ValidationError("Only returned loans can be deleted.")
        self.delete()

    @staticmethod
    def random_days_between(lo: int, hi: int) -> int:
        return random.randint(lo, hi)
