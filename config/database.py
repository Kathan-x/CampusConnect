"""
MongoDB connection setup using PyMongo.
Creates unique indexes so duplicate event_id / registration_id / duplicate
student-event registration are rejected at the database level.
"""
import os
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "campusconnect")

_client = None
_db = None


def get_db():
    """Return a cached MongoDB database handle, creating indexes on first use."""
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        _client.admin.command("ping")  # fail fast if MongoDB is unreachable
        _db = _client[DB_NAME]
        _ensure_indexes(_db)
    return _db


def _ensure_indexes(db):
    db.events.create_index([("event_id", ASCENDING)], unique=True)
    db.registrations.create_index([("registration_id", ASCENDING)], unique=True)
    db.registrations.create_index(
        [("event_id", ASCENDING), ("enrollment_number", ASCENDING)], unique=True
    )


def check_connection():
    """Used at app startup to give a clear error if MongoDB is down."""
    try:
        get_db()
        return True
    except ConnectionFailure:
        return False
