from flask import render_template, url_for, flash, redirect, request, abort, session, make_response
from flask.json import jsonify
from zoom_app import app, db, bcrypt
from zoom_app.forms import RegistrationForm, LoginForm, MeetingRegistrationForm, MetaMeetingForm, UpdateAccountForm
from zoom_app.models import User, MeetingForm, Registrant
from flask_login import login_user, current_user, logout_user, login_required
from zoomus import ZoomClient
import time
import json


# Custom Jinja functions
@app.context_processor
def utility_processor():
    def list_length(lst):
        return len(lst)
    
    def return_idx_in_list(item, lst):
        return lst.index(item)
    return dict(list_length=list_length, return_idx_in_list=return_idx_in_list)


@app.route("/")
@app.route("/home")
def home():
    if current_user.is_authenticated:
        zoom_client = ZoomClient(current_user.api_key, current_user.api_secret)
        meeting_list_response = zoom_client.meeting.list(user_id="me")

        # Grab all meetings associated with this API credentials
        meetings = json.loads(meeting_list_response.content)['meetings']
        meetings_id = [meeting["id"] for meeting in meetings]

        # Get all forms that this user owns that are associated with this API client
        meeting_forms = MeetingForm.query\
            .join(User, MeetingForm.user_id == current_user.id)\
            .filter(MeetingForm.meeting_id.in_(meetings_id)).all()
    else:
        meetings = []
        meeting_forms = []
    return render_template('home.html', meetings=meetings, meeting_forms=meeting_forms)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            username = form.username.data,
            email=form.email.data,
            password=hashed_password,
            api_key=form.api_key.data,
            api_secret=form.api_secret.data
        )
        db.session.add(user)
        db.session.commit()
        flash(f'Your account has been created. You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            flash('Login successful', 'success')
            return redirect(next_page) if next_page else redirect(url_for("home"))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        # Commit changes to the db
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.api_key = form.api_key.data
        current_user.api_secret = form.api_secret.data
        db.session.commit()

        flash("Updated account details", "success")
        return redirect(url_for("home"))

    # Populate the form with existing data if GET
    if request.method == "GET":
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.api_key.data = current_user.api_key
        form.api_secret.data = current_user.api_secret

    return render_template("account.html", legend="View/Update Account", title="Account Details", form=form)


@app.route("/logout", methods=['GET', 'POST'])
def logout():
    logout_user()
    return redirect(url_for("home"))


# ------- NEW ROUTES FOR THE FORMS ----------------

# Route to create a form
@app.route('/meetingforms/create/', defaults={'meeting_id': None, 'meeting_name': None}, methods=['GET', 'POST'])
@app.route("/meetingforms/create/<meeting_id>/<meeting_name>", methods=['GET', 'POST'])
@login_required
def new_form(meeting_id, meeting_name):
    form = MetaMeetingForm()
    if form.validate_on_submit():
        meeting_form = MeetingForm(
            meeting_id = int(form.meeting_id.data),
            meeting_form_name = form.meeting_form_name.data,
            creator = current_user,
            active = True
        )
        db.session.add(meeting_form)
        db.session.commit()
        flash(f"Created new form for '{meeting_name}'", "success")
        return redirect(url_for("home"))
    if request.method == "GET":
        form.meeting_id.data = meeting_id
    return render_template("create_form.html", title="New Form", legend=f"New Form for {meeting_name}", form=form)


# Route to view a form (from the creator POV) and see all registrants
@app.route("/meetingforms/<int:meeting_form_id>", methods=['GET', 'POST'])
@login_required
def meeting_form(meeting_form_id):
    meeting_form = MeetingForm.query.get_or_404(meeting_form_id)

    zoom_client = ZoomClient(current_user.api_key, current_user.api_secret)
    meeting_list_response = zoom_client.meeting.list(user_id="me")

    # Grab all meetings associated with this API credentials
    meetings = json.loads(meeting_list_response.content)['meetings']
    allowed_meetings_id = [meeting["id"] for meeting in meetings]

    # If user did not create this form
    if meeting_form.creator != current_user:
        abort(403)

    # If user does not have access to this meeting anymore
    if meeting_form.meeting_id not in allowed_meetings_id:
        abort(403)

    return render_template(
        "meeting_form.html",
        title=meeting_form.meeting_form_name,
        meeting_form=meeting_form,
        view_link=f"{request.base_url}/view"
    )


# Route to activate/deactivate a form
@app.route("//meetingforms/<int:meeting_form_id>/toggle", methods=["POST"])
@login_required
def toggle_meeting_form(meeting_form_id):
    meeting_form = MeetingForm.query.get_or_404(meeting_form_id)
    if meeting_form.creator != current_user:
        abort(403)
    meeting_form.active = not meeting_form.active
    db.session.commit()
    return redirect(url_for("meeting_form", meeting_form_id=meeting_form.id))


# Route to view and submit the form (from registrant POV). On POST will call API to actually add the user to the meeting
@app.route("/meetingforms/<int:meeting_form_id>/view", methods=['GET', 'POST'])
def view_meeting_form(meeting_form_id):
    # Grab meeting form and the creator
    meeting_form = MeetingForm.query.get_or_404(meeting_form_id)
    creator = meeting_form.creator

    # Make zoom client using creator's credentials
    zoom_client = ZoomClient(creator.api_key, creator.api_secret)

    # If the form is not active
    if not meeting_form.active:
        flash("This form is not available to fill out anymore.", "info")
        return redirect(url_for("home"))
    
    # If form is still active
    form = MeetingRegistrationForm()
    if form.validate_on_submit():

        # Check if the registrant already signed up for the meeting through any other form.
        registrant = Registrant.query\
            .join(MeetingForm, Registrant.meeting_form_id == MeetingForm.id)\
            .filter(MeetingForm.meeting_id==meeting_form.meeting_id).first()
        
        # If so, they can't sign up again on this form anymore
        if registrant:
            flash("You already signed up for this meeting through one of our forms.", "danger")
            return redirect(url_for("view_meeting_form", meeting_form_id=meeting_form.id))

        # If not, then send a request to the server through the Zoom client
        request_body = {
            "email": form.email.data,
            "first_name": form.first_name.data,
            "last_name": form.last_name.data
        }

        response = zoom_client.meeting.post_request(f"/meetings/{meeting_form.meeting_id}/registrants", data=request_body)
        response_json = json.loads(response.content)

        # If the status code is 200, add the registrant's info to the DB
        print(response_json)
        if response_json["code"] == 200:
            registrant = Registrant(
                email=form.email.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                address=form.address.data,
                job_title=form.job_title.data,
                register_form=meeting_form
            )
            db.session.add(registrant)
            db.session.commit()
            return render_template("meeting_register_complete.html")
        else:
            flash(f"Error: {response_json['message']}")
    return render_template("meeting_form_submittable.html", form=form, title="Meeting Form", legend=f"{meeting_form.meeting_form_name}")
