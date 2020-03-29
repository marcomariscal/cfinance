from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
db = SQLAlchemy()


DEFAULT_IMG_URL = 'https://i.stack.imgur.com/34AD2.jpg'


class User(db.Model):
    """User."""

    __tablename__ = "users"

    id = db.Column(db.Integer,
                   primary_key=True)

    api_key = db.Column(db.Text,
                        nullable=False, unique=True)

    username = db.Column(db.Text,
                         nullable=False, unique=True)

    password = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<User #{self.id}: {self.username}>"

    @classmethod
    def signup(cls, api_key, username, password):
        """Sign up user using coinbase pro api key, username, and password.

        Hashes api_key and password, then adds user to system.
        """

        hashed_api_key = bcrypt.generate_password_hash(api_key).decode('UTF-8')
        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')

        user = User(
            api_key=hashed_api_key,
            username=username,
            password=hashed_pwd
        )

        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username, password):
        """Find user with `username` and `password`.

        This is a class method (call it on the class, not an individual user.)
        It searches for a user whose password hash matches this password
        and, if it finds such a user, returns that user object.

        If can't find matching user (or if password is wrong), returns False.
        """

        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False


def connect_db(app):
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """

    db.app = app
    db.init_app(app)
