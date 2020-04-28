from flask import render_template, url_for, flash, redirect, request, abort
from zoom_app import app, db, bcrypt
from zoom_app.forms import RegistrationForm, LoginForm, MeetingRegistrationForm, MetaMeetingForm
from zoom_app.models import User, MeetingForm, Registrant
from flask_login import login_user, current_user, logout_user, login_required
from zoom_app.env import *  # Use a library to fix this later



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
    meeting_forms = current_user.meeting_forms if current_user.is_authenticated else []
    return render_template('home.html', meeting_forms=meeting_forms)


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
@app.route("/meetingforms/create", methods=['GET', 'POST'])
@login_required
def new_form():
    form = MetaMeetingForm()
    if form.validate_on_submit():
        meeting_form = MeetingForm(
            meeting_id = int(form.meeting_id.data),
            meeting_name = form.meeting_name.data,
            creator = current_user,
            active = True
        )
        db.session.add(meeting_form)
        db.session.commit()
        flash(f"Created new form for meeting {form.meeting_id.data}", "success")
        return redirect(url_for("home"))
    return render_template("create_form.html", title="New Form", legend="New Form", form=form)


# Route to view a form (from the creator POV) and see all registrants
@app.route("/meetingforms/<int:meeting_form_id>", methods=['GET', 'POST'])
@login_required
def meeting_form(meeting_form_id):
    meeting_form = MeetingForm.query.get_or_404(meeting_form_id)
    if meeting_form.creator != current_user:
        abort(403)
    return render_template(
        "meeting_form.html",
        title=meeting_form.meeting_name,
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
