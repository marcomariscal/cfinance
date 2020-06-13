"""Seed file to make sample data for db."""

from models import db, User
from app import app

# Create all tables
db.drop_all()
db.create_all()

DEMO_API_KEY = 'dbe5354088533e5d425613136255a29a'
DEMO_SECRET = 'y9tLKbTTfxzNirvFTwYqkyFPFGoavuCm6cpsKIKaLAYnjPpf9Rxf7jGrDc7XPcGhAdZ5JkfoJDb+QaVJd+xBig=='
DEMO_PASSPHRASE = 'pass'

user = User.signup(api_key=DEMO_API_KEY, api_secret=DEMO_SECRET,
                   api_passphrase=DEMO_PASSPHRASE)

db.session.add(user)
db.session.commit()
