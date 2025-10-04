from flask import Blueprint

bp = Blueprint("books", __name__, template_folder="../../templates")

from . import routes  
