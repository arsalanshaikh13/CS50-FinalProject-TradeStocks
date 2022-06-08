from application import db
from datetime import datetime
from datetime import datetime
from zoneinfo import ZoneInfo


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    username = db.Column(db.String(30), nullable=False, unique=True, index=True)
    email = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False, unique=True)
    cash = db.Column(db.Integer, default=10000)
    time = db.Column(db.DateTime(timezone=True), default=datetime.now(tz=ZoneInfo('Asia/Kolkata')), nullable=False)
    user_profile = db.relationship('User_Profile', backref='users', lazy=True)
    transaction = db.relationship('Transaction', backref='users',  lazy='dynamic')

    def __repr__(self):
        return '<User %r>' % self.username


class User_Profile(db.Model):
    __tablename__ = 'user_profile'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    fullname = db.Column(db.String(30))
    birthdate = db.Column(db.Date)
    profile_picture = db.deferred(db.Column(db.Text))
    phone_number = db.Column(db.Numeric)
    address = db.Column(db.String(255))

    __table_args__= (
        db.PrimaryKeyConstraint(user_id, fullname),
    )

    def __repr__(self):
        return '<User_Profile %r>' % self.fullname


class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    symbol = db.Column(db.String(10), index=True)
    company = db.Column(db.String(30))
    share_qty = db.Column(db.Integer, nullable=False)
    share_price = db.Column(db.Integer, nullable=False)
    total_cost = db.Column(db.Integer, nullable=False)
    transaction_type = db.Column(db.Enum('BUY', 'SELL','ADD CASH', 'REDEEM CASH'), nullable=False)
    transaction_time = db.Column(db.DateTime(timezone=True), default=datetime.now(tz=ZoneInfo('Asia/Kolkata')), nullable=False)

    def __repr__(self):
        return '<Transaction %r>' % self.user_id

db.create_all()
