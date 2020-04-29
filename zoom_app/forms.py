from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from zoom_app.models import User, Registrant


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField("Sign up")


    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("That username is taken, please choose a different one")

    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("That email is taken, please choose a different one")


class LoginForm(FlaskForm):
    email = StringField("Email",
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField("Login")


class MetaMeetingForm(FlaskForm):
    meeting_id = StringField("Meeting ID (from Zoom)", validators=[DataRequired()])  # Should convert back to int before commiting
    meeting_form_name = StringField("Name for Form", validators=[DataRequired()])
    submit = SubmitField("Create Meeting Form")


class MeetingRegistrationForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    job_title = StringField("Job Title")
    address = StringField("Address (street name)")
    submit = SubmitField("Sign up for meeting")


    def validate_email(self, email):
        registrant = Registrant.query.filter_by(email=email.data).first()
        if registrant:
            raise ValidationError("You have already signed up for this meeting.")

