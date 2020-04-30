from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from zoom_app.models import User, Registrant
from zoomus import ZoomClient
import json


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    api_key = StringField('API Key (from Zoom)', validators=[DataRequired()])
    api_secret = StringField('API Secret (from Zoom)', validators=[DataRequired()])
    submit = SubmitField("Sign up")


    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("That username is taken, please choose a different one")

    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("That email is taken, please choose a different one")


    def validate(self):
        """
        Send a test request to see if this API credentials are valid
        """
        rv = FlaskForm.validate(self)
        if not rv:
            return False

        client = ZoomClient(api_key=self.api_key.data, api_secret=self.api_secret.data)
        response = json.loads(client.user.list().content)

        # If invalid credentials, raise error to the form.
        if response.get("code") == 124:
            self.api_key.errors.append(response.get("message"))
            self.api_secret.errors.append(response.get("message"))
            return False

        return True


class UpdateAccountForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    api_key = StringField('API Key (from Zoom)', validators=[DataRequired()])
    api_secret = StringField('API Secret (from Zoom)', validators=[DataRequired()])
    submit = SubmitField("Update your Account")


    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')


    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')


    def validate(self):
        """
        Send a test request to see if this API credentials are valid
        """
        rv = FlaskForm.validate(self)
        if not rv:
            return False

        client = ZoomClient(api_key=self.api_key.data, api_secret=self.api_secret.data)
        response = json.loads(client.user.list().content)

        # If invalid credentials, raise error to the form.
        if response.get("code") != 200:
            self.api_key.errors.append(response.get("message"))
            self.api_secret.errors.append(response.get("message"))
            return False

        return True


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


    def validate_meeting_id(self, meeting_id):
        client = ZoomClient(api_key=current_user.api_key, api_secret=current_user.api_secret)
        response = json.loads(client.meeting.get(id=meeting_id.data).content)
        if response.get("code") in [300, 3001]:
            raise ValidationError(response.get("message"))


class MeetingRegistrationForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    job_title = StringField("Job Title")
    address = StringField("Address (street name)")
    submit = SubmitField("Sign up for meeting")

