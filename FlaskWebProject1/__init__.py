"""
The flask application package.
"""

from flask import Flask

from .config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

# Initialize database (creates tables and demo data if empty)
from .db import init_db
init_db()

# Register routes
import FlaskWebProject1.views
