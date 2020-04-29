from flask import render_template, url_for, flash, redirect, request, abort, session, make_response
from flask.json import jsonify
from zoom_app import app, db, bcrypt
from zoom_app.forms import RegistrationForm, LoginForm, MeetingRegistrationForm, MetaMeetingForm
from zoom_app.models import User, MeetingForm, Registrant
from flask_login import login_user, current_user, logout_user, login_required
from zoom_app.env import *  # Use a library to fix this later
from requests_oauthlib import OAuth2Session
import time


# Custom Jinja functions
@app.context_processor
def utility_processor():
    def list_length(lst):
        return len(lst)
    
    def return_idx_in_list(item, lst):
        return lst.index(item)
    return dict(list_length=list_length, return_idx_in_list=return_idx_in_list)


# Zoom OAuth Authorization. Followed from example found here:
# https://requests-oauthlib.readthedocs.io/en/latest/examples/real_world_example.html#real-example

@app.route("/zoomauth")
def zoom_auth():
    """Step 1: User Authorization.

    Redirect the user/resource owner to the OAuth provider (i.e. Zoom)
    using an URL with a few key OAuth parameters.
    """
    zoom = OAuth2Session(client_id, redirect_uri=redirect_uri)
    authorization_url, state = zoom.authorization_url(authorization_base_url)
    print(authorization_url)

    # State is used to prevent CSRF, keep this for later.
    session['oauth_state'] = state
    return redirect(authorization_url)


# Step 2: User authorization, this happens on the provider.

@app.route("/zoomcallback", methods=["GET"])
def zoom_callback():
    """ Step 3: Retrieving an access token.

    The user has been redirected back from the provider to your registered
    callback URL. With this redirection comes an authorization code included
    in the redirect URL. We will use that to obtain an access token.
    """

    zoom = OAuth2Session(client_id, state=session['oauth_state'], redirect_uri=redirect_uri)
    token = zoom.fetch_token(token_url, client_secret=client_secret, authorization_response=request.url)

    # At this point you can fetch protected resources but lets save
    # the token and show how this is done from a persisted token.
    session['oauth_token'] = token

    return redirect(url_for('home'))


@app.route("/zoomrefresh", methods=["GET"])
def zoom_refresh():
    """Refreshing an OAuth 2 token using a refresh token.
    """
    token = session['oauth_token']

    extra = {
        'client_id': client_id,
        'client_secret': client_secret,
    }
    print("refresh")
    zoom = OAuth2Session(client_id, token=token)
    session['oauth_token'] = zoom.refresh_token(refresh_url, **extra)
    flash("Refreshed access to Zoom Account!", "success")
    return redirect(url_for("home"))


def check_zoom_auth_status():
    return "oauth_token" in session.keys()


def need_refresh():
    if check_zoom_auth_status():
        token = session['oauth_token']
        return time.time() > token["expires_at"]
    return False


def return_zoom_instance():
    return OAuth2Session(client_id, token=session['oauth_token'])


def get_all_meetings(zoom_instance):
    if zoom_instance:
        return zoom_instance.get("https://api.zoom.us/v2/users/me/meetings").json()["meetings"]
    else:
        return []


@app.route("/")
@app.route("/home")
def home():
    zoom_status = check_zoom_auth_status()
    refresh_status = need_refresh()
    if zoom_status and refresh_status:
        return redirect(url_for('zoom_refresh'))
        
    zoom = return_zoom_instance() if zoom_status else None
    meetings = get_all_meetings(zoom)
    meeting_forms = current_user.meeting_forms if current_user.is_authenticated else []
    return render_template('home.html', meetings=meetings, meeting_forms=meeting_forms, zoom_status=zoom_status, refresh_status=refresh_status)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username = form.username.data, email=form.email.data, password=hashed_password)
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
    form.meeting_id.data = meeting_id
    return render_template("create_form.html", title="New Form", legend=f"New Form for {meeting_name}", form=form)


# Route to view a form (from the creator POV) and see all registrants
@app.route("/meetingforms/<int:meeting_form_id>", methods=['GET', 'POST'])
@login_required
def meeting_form(meeting_form_id):
    meeting_form = MeetingForm.query.get_or_404(meeting_form_id)
    if meeting_form.creator != current_user:
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
    meeting_form = MeetingForm.query.get_or_404(meeting_form_id)
    # If the form is not active
    if not meeting_form.active:
        flash("This form is not available to fill out anymore.", "info")
        return redirect(url_for("home"))
    
    # If form is still active
    form = MeetingRegistrationForm()
    if form.validate_on_submit():
        
        # Send the API request here
        # If successful, then add registrant to db
        # If not, than just redirect back to the form
        # For now, just add the registrant
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
        return render_template("meeting_register_complete.html", meeting_form_name=meeting_form.name)
    return render_template("meeting_form_submittable.html", form=form, title="Meeting Form", legend=f"Meeting Form for {meeting_form.meeting_name}")


# Authorizing Zoom:
