# This file handles sign up, login, and logout.
# It checks the form details and saves new members to the database.
# It also controls who can access certain pages.
from flask import Blueprint, render_template, redirect, url_for, request, flash
from . import db
from .models import User, SharedPassword, poker_members
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

auth = Blueprint("auth", __name__)


@auth.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash("Logged in!", category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Password is incorrect.', category='error')
        else:
            flash('Email does not exist.', category='error')

    return render_template("login.html", user=current_user)

@auth.route("/sign-up", methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get("email").lower()
        username = request.form.get("username").lower()
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")
        shared_password = request.form.get("shared_password")

        email_exists = User.query.filter_by(email=email).first()
        username_exists = User.query.filter_by(username=username).first()
        stored_password = SharedPassword.query.first().password

        if email_exists:
            flash('Email is already in use.', category='error')
        elif len(username) > 14:
            flash('Username must not be more than 14 characters.', category='error')
        elif len(password1) > 14:
            flash('Password must not be more than 14 characters.', category='error')
        elif username.isdigit() or len(set(username)) == 1:
            flash('Username cannot be all numbers or the same character.', category='error')
        elif username_exists:
            flash('Username is already in use.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match!', category='error')
        elif len(username) < 2:
            flash('Username is too short.', category='error')
        elif len(password1) < 6:
            flash('Password is too short.', category='error')
        elif len(email) < 4:
            flash("Email is invalid.", category='error')
        elif shared_password != stored_password:
            flash("Invalid shared password.", category='error')
        else:
            new_user = User(email=email,
                            username=username,
                            password=generate_password_hash(password1, method='pbkdf2:sha256'),
                            admin = False
                            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('User created!')
            return redirect(url_for('views.home'))

    return render_template("signup.html", user=current_user)

@auth.route("/tcdcards-sign-up", methods=['GET', 'POST'])
def tcdcards_sign_up():
    if request.method == 'POST':
        email = request.form.get("email").lower()
        first_name = request.form.get("first_name").lower()
        last_name = request.form.get("last_name").lower()
        course = request.form.get("course").lower()
        year = request.form.get("year")  # No need for .lower(), convert to int if needed
        sex = request.form.get("sex").lower()

        # Validation
        if not email.endswith("@tcd.ie"):
            flash('Email must end with @tcd.ie', category='error')
        elif len(first_name) > 14:
            flash('First name must not be more than 14 characters.', category='error')
        elif len(last_name) > 14:
            flash('Last name must not be more than 14 characters.', category='error')
        elif len(first_name) < 2:
            flash('First name is too short.', category='error')
        elif len(last_name) < 2:
            flash('Last name is too short.', category='error')
        elif len(email) < 2:
            flash("Email is invalid.", category='error')
        elif year not in ['1', '2', '3', '4', '5', '6']:  # Validate year is within range
            flash("Invalid year selected.", category='error')
        elif sex not in ['male', 'female', 'other']:  # Validate sex is one of the expected values
            flash("Invalid gender selected.", category='error')
        else:
            # Create a new poker_members record
            new_member = poker_members(email=email,
                                       first_name=first_name,
                                       last_name=last_name,
                                       course=course,
                                       year=year,  # Keep as string, consistent with model definition
                                       sex=sex)
            db.session.add(new_member)
            db.session.commit()
            flash('Member successfully created!')
            return redirect(url_for('views.complete_signup'))

    return render_template("tcdcards_signup.html", user=current_user)


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("views.home"))