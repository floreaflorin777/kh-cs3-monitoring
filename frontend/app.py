"""
Knowledge Hub Monitor - Web Frontend (CS3, week 1 scaffold)

This is the Flask web application that staff will use to view monitoring data.
Week 1 produces only routes, templates, and basic styling. Authentication and
API calls are added in week 2 and week 3.
"""

import os
from flask_session import Session
from flask import Flask, render_template, redirect, url_for, session, request
from dotenv import load_dotenv
import msal
import uuid
from functools import wraps

# Load variables from a local .env file if one exists. The file is git-ignored.
load_dotenv()

app = Flask(__name__)

# Secret key is used by Flask to sign session cookies. In production this comes
# from an environment variable (Container Apps secret). The fallback exists only
# so the app still starts during local development.
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
# Entra ID / MSAL configuration
ENTRA_TENANT_ID = os.environ.get("ENTRA_TENANT_ID")
ENTRA_CLIENT_ID = os.environ.get("ENTRA_CLIENT_ID")
ENTRA_CLIENT_SECRET = os.environ.get("ENTRA_CLIENT_SECRET")
AUTHORITY = f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}"
REDIRECT_PATH = "/getAToken"
SCOPE = ["User.Read"]

def _build_msal_app(cache=None):
    """Construct a MSAL ConfidentialClientApplication, optionally with a token cache."""
    return msal.ConfidentialClientApplication(
        ENTRA_CLIENT_ID,
        authority=AUTHORITY,
        client_credential=ENTRA_CLIENT_SECRET,
        token_cache=cache,
    )


def _load_cache():
    """Load the user's MSAL token cache from the Flask session, if any."""
    cache = msal.SerializableTokenCache()
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    return cache


def _save_cache(cache):
    """Persist the cache back to the session if it changed."""
    if cache.has_state_changed:
        session["token_cache"] = cache.serialize()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/")
def index():
    """Landing page. Public. No authentication required."""
    return render_template("index.html")


@app.route("/dashboard")
@login_required
def dashboard():
    """
    Monitoring dashboard. In week 2 this route will be protected with the
    Entra ID login_required decorator. In week 3 the placeholder data below
    will be replaced with real metrics fetched from the backend API.
    """
    placeholder_metrics = {
        "system_metrics_available": False,
        "container_metrics_available": False,
        "last_updated": "Not yet connected to the API",
    }
    return render_template("dashboard.html", metrics=placeholder_metrics)


@app.route("/login")
def login():
    session["state"] = str(uuid.uuid4())
    auth_url = _build_msal_app().get_authorization_request_url(
        SCOPE,
        state=session["state"],
        redirect_uri=url_for("authorized", _external=True),
    )
    return redirect(auth_url)

@app.route(REDIRECT_PATH)
def authorized():
    # CSRF protection: the state we sent must match the state Entra ID returned.
    if request.args.get("state") != session.get("state"):
        return redirect(url_for("index"))

    # Did Entra ID report an error?
    if "error" in request.args:
        return f"Authentication error: {request.args.get('error_description', 'unknown')}", 401

    # Exchange the authorization code for tokens.
    cache = _load_cache()
    result = _build_msal_app(cache).acquire_token_by_authorization_code(
        request.args.get("code"),
        scopes=SCOPE,
        redirect_uri=url_for("authorized", _external=True),
    )
    if "error" in result:
        return f"Token exchange error: {result.get('error_description', 'unknown')}", 401

    # Store the user's identity claims and persist the cache.
    session["user"] = result.get("id_token_claims")
    _save_cache(cache)

    # Send them to the dashboard now that they are signed in.
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    # Clear local session (user, token cache, state).
    session.clear()

    # Send the user to Entra ID's logout endpoint so the Microsoft sign-in
    # is also cleared. After Microsoft signs them out, they come back to our
    # index page.
    return redirect(
        f"{AUTHORITY}/oauth2/v2.0/logout"
        f"?post_logout_redirect_uri={url_for('index', _external=True)}"
    )


@app.route("/health")
def health():
    """
    Health-check endpoint. Returns 200 if the app is running.
    Container Apps and Docker use this kind of endpoint for liveness probes.
    """
    return {"status": "ok"}, 200


if __name__ == "__main__":
    # Local development entry point. Run with: python app.py
    # In a container, gunicorn serves this same app instead.
    app.run(host="localhost", port=5000, debug=True)
