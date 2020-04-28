from zoom_app import db
from zoom_app.models import User, MeetingForm, Registrant

db.drop_all()
db.create_all()