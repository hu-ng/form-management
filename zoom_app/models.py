from datetime import datetime
from zoom_app import db, login_manager
from flask_login import UserMixin
from sqlalchemy.dialects.mysql import BIGINT


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    meeting_forms = db.relationship('MeetingForm', backref='creator', lazy=True)
    api_key = db.Column(db.String(120), nullable=False)
    api_secret = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"


# A user has many meeting forms
class MeetingForm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(BIGINT(unsigned=True), nullable=False)
    meeting_form_name = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    active = db.Column(db.Boolean, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    registrants = db.relationship('Registrant', backref='register_form', lazy=True)

    def __repr__(self):
        return f"Meeting {self.meeting_form_name}, meeting id: {self.meeting_id}"
    

# A meeting has many registrants
class Registrant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(50))
    job_title = db.Column(db.String(50))
    date_registered = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    meeting_form_id = db.Column(db.Integer, db.ForeignKey('meeting_form.id'), nullable=False)

    def __repr__(self):
        return f"Meeting registrant {self.first_name} {self.last_name}, {self.email}"