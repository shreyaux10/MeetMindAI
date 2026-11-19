
import os
import json
import sqlite3
import time
from datetime import datetime
import whisper
from werkzeug.utils import secure_filename

from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
    flash
)

from dotenv import load_dotenv
from google import genai
from google.genai import errors

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    current_user,
    login_required
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from auth import (
    User,
    get_user_by_id,
    get_user_by_email,
    init_auth_db,
    get_auth_db
)


# =====================================
# CONFIGURATION
# =====================================

load_dotenv()

app = Flask(__name__)

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is missing. Add it to your .env file."
    )

app.config["SECRET_KEY"] = SECRET_KEY

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

DATABASE = "meetmind.db"
UPLOAD_FOLDER = "uploads"
ALLOWED_AUDIO_EXTENSIONS = {
    "mp3", "wav", "m4a", "ogg", "flac", "mp4", "webm"
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key) if api_key else None

MODEL_NAME = "gemini-3.8-flash"


# =====================================
# FLASK LOGIN CONFIGURATION
# =====================================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"

login_manager.login_message = "Please log in to access your workspace."

login_manager.login_message_category = "error"


@login_manager.user_loader
def load_user(user_id):

    return get_user_by_id(user_id)


# =====================================
# DATABASE CONNECTION
# =====================================

def get_db():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


# =====================================
# INITIALIZE DATABASE
# =====================================

def init_db():

    with get_db() as db:

        db.execute("""
            CREATE TABLE IF NOT EXISTS meetings (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                title TEXT NOT NULL,

                attendees TEXT,

                transcript TEXT NOT NULL,

                summary TEXT NOT NULL,

                key_points TEXT,

                decisions TEXT,

                action_items TEXT,

                created_at TEXT NOT NULL

            )
        """)

    print("Meeting database initialized!")


# =====================================
# FORMAT MEETING DATA
# =====================================

def meeting_to_dict(row):

    meeting = dict(row)

    for field in [
        "key_points",
        "decisions",
        "action_items"
    ]:

        try:

            meeting[field] = json.loads(
                meeting[field] or "[]"
            )

        except (TypeError, json.JSONDecodeError):

            meeting[field] = []

    return meeting


# =====================================
# USER SIGNUP
# =====================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if current_user.is_authenticated:

        return redirect(url_for("home"))

    if request.method == "POST":

        name = request.form.get(
            "name", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get(
            "password", ""
        )

        if not name or not email or not password:

            flash(
                "Please fill in all fields.",
                "error"
            )

            return redirect(url_for("signup"))

        if len(name) > 100 or len(email) > 254:

            flash(
                "Name or email is too long.",
                "error"
            )

            return redirect(url_for("signup"))

        if "@" not in email or "." not in email.rsplit("@", 1)[-1]:

            flash(
                "Please enter a valid email address.",
                "error"
            )

            return redirect(url_for("signup"))

        if len(password) < 8:

            flash(
                "Password must contain at least 8 characters.",
                "error"
            )

            return redirect(url_for("signup"))

        password_hash = generate_password_hash(password)

        created_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )

        try:

            with get_auth_db() as db:

                db.execute("""

                    INSERT INTO users (
                        name,
                        email,
                        password_hash,
                        created_at
                    )

                    VALUES (?, ?, ?, ?)

                """, (
                    name,
                    email,
                    password_hash,
                    created_at
                ))

            flash(
                "Account created successfully! Please log in.",
                "success"
            )

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            flash(
                "This email is already registered.",
                "error"
            )

            return redirect(url_for("signup"))

    return render_template("signup.html")


# =====================================
# USER LOGIN
# =====================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:

        return redirect(url_for("home"))

    if request.method == "POST":

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get(
            "password", ""
        )

        user = get_user_by_email(email)

        if user and check_password_hash(
            user.password_hash,
            password
        ):

            login_user(user)

            return redirect(url_for("home"))

        flash(
            "Invalid email or password.",
            "error"
        )

        return redirect(url_for("login"))

    return render_template("login.html")


# =====================================
# USER LOGOUT
# =====================================

@app.route("/logout", methods=["POST"])
@login_required
def logout():

    logout_user()

    flash(
        "You have been logged out successfully.",
        "success"
    )

    return redirect(url_for("login"))


# =====================================
# USER PROFILE & SETTINGS
# =====================================

@app.route("/settings")
@login_required
def settings():

    return render_template("settings.html")


# =====================================
# UPDATE PROFILE INFORMATION
# =====================================

@app.route("/update-profile", methods=["POST"])
@login_required
def update_profile():

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not name or not email:
        flash("Please fill in all fields.", "error")
        return redirect(url_for("settings"))

    if len(name) > 100 or len(email) > 254:
        flash("Name or email is too long.", "error")
        return redirect(url_for("settings"))

    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("settings"))

    try:
        with get_auth_db() as db:

            db.execute("""
                UPDATE users
                SET name = ?, email = ?
                WHERE id = ?
            """, (
                name,
                email,
                current_user.id
            ))

        # Update the current logged-in user object
        current_user.name = name
        current_user.email = email

        flash("Profile updated successfully!", "success")

    except sqlite3.IntegrityError:
        flash("This email is already registered.", "error")

    return redirect(url_for("settings"))


# =====================================
# CHANGE ACCOUNT PASSWORD
# =====================================

@app.route("/change-password", methods=["POST"])
@login_required
def change_password():

    current_password = request.form.get(
        "current_password", ""
    )

    new_password = request.form.get(
        "new_password", ""
    )

    confirm_password = request.form.get(
        "confirm_password", ""
    )

    if not current_password or not new_password or not confirm_password:
        flash("Please fill in all password fields.", "error")
        return redirect(url_for("settings"))

    if not check_password_hash(
        current_user.password_hash,
        current_password
    ):
        flash("Your current password is incorrect.", "error")
        return redirect(url_for("settings"))

    if len(new_password) < 8:
        flash("New password must contain at least 8 characters.", "error")
        return redirect(url_for("settings"))

    if new_password != confirm_password:
        flash("New passwords do not match.", "error")
        return redirect(url_for("settings"))

    new_password_hash = generate_password_hash(new_password)

    with get_auth_db() as db:

        db.execute("""
            UPDATE users
            SET password_hash = ?
            WHERE id = ?
        """, (
            new_password_hash,
            current_user.id
        ))

    # Update the current user object
    current_user.password_hash = new_password_hash

    flash("Password changed successfully!", "success")

    return redirect(url_for("settings"))

# =====================================
# HOME PAGE
# =====================================

@app.route("/")
@login_required
def home():

    return render_template("index.html")


# =====================================
# BACKEND HEALTH CHECK
# =====================================

@app.route("/api/health")
def health():

    return jsonify({

        "status": "running",

        "application": "MeetMind AI",

        "ai_provider": "Google Gemini",

        "ai_configured": client is not None

    })


# =====================================
# GET ALL MEETINGS
# =====================================

@app.route("/api/meetings")
@login_required
def get_meetings():

    with get_db() as db:

        rows = db.execute("""

            SELECT *
            FROM meetings
            WHERE user_id = ?
            ORDER BY id DESC

        """, (
            current_user.id,
        )).fetchall()

    return jsonify([

        meeting_to_dict(row)

        for row in rows

    ])


# =====================================
# GET SINGLE MEETING
# =====================================

@app.route("/api/meetings/<int:meeting_id>")
@login_required
def get_meeting(meeting_id):

    with get_db() as db:

        row = db.execute("""

            SELECT *
            FROM meetings
            WHERE id = ?
            AND user_id = ?

        """, (
            meeting_id,
            current_user.id

        )).fetchone()

    if row is None:

        return jsonify({

            "error": "Meeting not found."

        }), 404

    return jsonify(meeting_to_dict(row))


# =====================================
# DELETE MEETING
# =====================================

@app.route("/api/meetings/<int:meeting_id>", methods=["DELETE"])
@login_required
def delete_meeting(meeting_id):

    with get_db() as db:

        cursor = db.execute("""
            DELETE FROM meetings
            WHERE id = ?
            AND user_id = ?
        """, (
            meeting_id,
            current_user.id
        ))

        if cursor.rowcount == 0:

            return jsonify({
                "error": "Meeting not found or access denied."
            }), 404

    return jsonify({
        "message": "Meeting deleted successfully.",
        "id": meeting_id
    })



# =====================================
# GEMINI MEETING ANALYSIS
# =====================================

@app.route("/api/transcribe", methods=["POST"])
@login_required
def transcribe_audio():

    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded."}), 400

    audio_file = request.files["audio"]

    if audio_file.filename == "":
        return jsonify({"error": "Please select an audio file."}), 400

    filename = secure_filename(audio_file.filename)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension not in ALLOWED_AUDIO_EXTENSIONS:
        return jsonify({"error": "Unsupported audio format."}), 400

    file_path = os.path.join(UPLOAD_FOLDER, filename)

    try:
        audio_file.save(file_path)

        model = whisper.load_model("base")
        result = model.transcribe(file_path)

        transcript = result["text"].strip()

        if not transcript:
            return jsonify({"error": "No speech detected in the audio."}), 400

        return jsonify({
            "success": True,
            "transcript": transcript
        })

    except Exception as e:
        print("Transcription error:", str(e))
        return jsonify({"error": "Audio transcription failed."}), 500

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            
@app.route("/api/analyze", methods=["POST"])
@login_required
def analyze_meeting():

    if client is None:

        return jsonify({

            "error": "Gemini API key is missing. Check your .env file."

        }), 503

    data = request.get_json(silent=True) or {}

    title = (
        data.get("title") or "Untitled Meeting"
    ).strip()

    attendees = (
        data.get("attendees") or ""
    ).strip()

    transcript = (
        data.get("transcript") or ""
    ).strip()

    if not transcript:

        return jsonify({

            "error": "Please enter meeting notes or a transcript."

        }), 400

    if len(transcript) > 100000:

        return jsonify({

            "error": "Transcript is too long. Please shorten it."

        }), 400

    # =====================================
    # GEMINI PROMPT
    # =====================================

    prompt = f"""

    You are MeetMind AI, an intelligent meeting assistant.

    Analyze the following meeting carefully.

    Meeting Title: {title}

    Attendees: {attendees or "Not specified"}

    Meeting Transcript:

    {transcript}

    Return a JSON object with these fields:

    1. summary: A concise professional meeting summary.

    2. key_points: A list of important discussion points.

    3. decisions: A list of decisions actually made.

    4. action_items: A list of tasks. Each task must contain:

       - task
       - assignee
       - deadline
       - status

    Rules:

    - Do not invent information.
    - Do not guess task owners or deadlines.
    - Use "Not specified" when details are missing.
    - Return empty arrays when no information is available.
    - Return valid JSON only.

    """

    # =====================================
    # JSON RESPONSE SCHEMA
    # =====================================

    response_schema = {

        "type": "OBJECT",

        "properties": {

            "summary": {
                "type": "STRING"
            },

            "key_points": {

                "type": "ARRAY",

                "items": {
                    "type": "STRING"
                }

            },

            "decisions": {

                "type": "ARRAY",

                "items": {
                    "type": "STRING"
                }

            },

            "action_items": {

                "type": "ARRAY",

                "items": {

                    "type": "OBJECT",

                    "properties": {

                        "task": {
                            "type": "STRING"
                        },

                        "assignee": {
                            "type": "STRING"
                        },

                        "deadline": {
                            "type": "STRING"
                        },

                        "status": {
                            "type": "STRING"
                        }

                    },

                    "required": [
                        "task",
                        "assignee",
                        "deadline",
                        "status"
                    ]

                }

            }

        },

        "required": [
            "summary",
            "key_points",
            "decisions",
            "action_items"
        ]

    }

    try:

        # =====================================
        # GEMINI API WITH AUTOMATIC RETRY
        # =====================================

        response = None

        for attempt in range(3):

            try:

                print(
                    f"Gemini request: Attempt {attempt + 1}/3"
                )

                response = client.models.generate_content(

                    model=MODEL_NAME,

                    contents=prompt,

                    config={

                        "response_mime_type": "application/json",

                        "response_schema": response_schema

                    }

                )

                break

            except errors.APIError as error:

                if error.code == 503 and attempt < 2:

                    wait_time = 5 * (attempt + 1)

                    print(
                        f"Gemini is busy. Retrying after {wait_time} seconds."
                    )

                    time.sleep(wait_time)

                else:

                    raise

        # =====================================
        # PROCESS GEMINI RESPONSE
        # =====================================

        if response is None or not response.text:

            return jsonify({

                "error": "Gemini returned an empty response. Please try again."

            }), 502

        result = json.loads(response.text)

        summary = str(result.get("summary", ""))

        key_points = result.get("key_points", [])

        decisions = result.get("decisions", [])

        action_items = result.get("action_items", [])

        if not isinstance(key_points, list):

            key_points = []

        if not isinstance(decisions, list):

            decisions = []

        if not isinstance(action_items, list):

            action_items = []

        # =====================================
        # SAVE MEETING FOR CURRENT USER
        # =====================================

        created_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )

        with get_db() as db:

            cursor = db.execute("""

                INSERT INTO meetings (

                    user_id,
                    title,
                    attendees,
                    transcript,
                    summary,
                    key_points,
                    decisions,
                    action_items,
                    created_at

                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

            """, (

                current_user.id,

                title,

                attendees,

                transcript,

                summary,

                json.dumps(key_points),

                json.dumps(decisions),

                json.dumps(action_items),

                created_at

            ))

            meeting_id = cursor.lastrowid

        # =====================================
        # RETURN RESULTS
        # =====================================

        return jsonify({

            "id": meeting_id,

            "title": title,

            "attendees": attendees,

            "transcript": transcript,

            "summary": summary,

            "key_points": key_points,

            "decisions": decisions,

            "action_items": action_items,

            "created_at": created_at

        })

    except json.JSONDecodeError:

        return jsonify({

            "error": "Gemini returned invalid JSON. Please try again."

        }), 502

    except errors.APIError as error:

        print("Gemini API error:", str(error))

        if error.code == 503:

            return jsonify({

                "error": "Gemini is temporarily busy. Please try again later."

            }), 503

        return jsonify({

            "error": "Gemini API request failed. Check the terminal for details."

        }), 502

    except Exception as error:

        print("MeetMind AI error:", str(error))

        return jsonify({

            "error": "Meeting analysis failed. Check the terminal for details."

        }), 500


# =====================================
# RUN APPLICATION
# =====================================

if __name__ == "__main__":

    init_db()

    init_auth_db()

    print("------------------------------------")
    print("          MEETMIND AI")
    print("       GOOGLE GEMINI AI")
    print("       USER AUTHENTICATION")
    print("------------------------------------")

    app.run(

        debug=True,

        port=5000

    )
