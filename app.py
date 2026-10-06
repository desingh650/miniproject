import csv
import os
import re
import tempfile
from flask import Flask, render_template, request, redirect, url_for, session, flash

# Initialize the Flask application
app = Flask(__name__)

# Secret key is required to handle sessions (user login state)
app.secret_key = "bca_simple_secret_key"


def get_csv_path(filename):
    """
    Returns a writable path for CSV files.
    On Vercel (read-only filesystem), uses the system temp directory (/tmp).
    """
    if os.environ.get("VERCEL"):
        return os.path.join(tempfile.gettempdir(), filename)

    try:
        # Check if local directory is writable
        test_path = os.path.join(os.getcwd(), ".perm_test")
        with open(test_path, "w") as f:
            f.write("test")
        if os.path.exists(test_path):
            os.remove(test_path)
        return os.path.join(os.getcwd(), filename)
    except (PermissionError, OSError):
        return os.path.join(tempfile.gettempdir(), filename)


# CSV file paths dynamically assigned for local vs Vercel
USERS_CSV = get_csv_path("users.csv")
CONTENTS_CSV = get_csv_path("contents.csv")


def initialize_csv_files():
    """Create CSV files with headers if they do not exist."""
    # Ensure users.csv exists
    if not os.path.exists(USERS_CSV):
        try:
            with open(USERS_CSV, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["name", "mobile", "email", "username", "password"])
        except Exception as e:
            print(f"Error initializing {USERS_CSV}: {e}")

    # Ensure contents.csv exists
    if not os.path.exists(CONTENTS_CSV):
        try:
            with open(CONTENTS_CSV, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["username", "title", "content"])
        except Exception as e:
            print(f"Error initializing {CONTENTS_CSV}: {e}")


# Run initialization
initialize_csv_files()


@app.route("/")
def index():
    """Default route: Redirects to home if logged in, else to login page."""
    if "username" in session:
        return redirect(url_for("home"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Registration Route: Handles user registration with Regular Expression validation."""
    initialize_csv_files()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        email = request.form.get("email", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # Regular Expressions for Data Validation
        mobile_regex = r"^[6-9]\d{9}$"
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        # Validate Mobile Number using Regex
        if not re.match(mobile_regex, mobile):
            flash("Invalid Mobile Number! Must be 10 digits starting with 6-9.", "error")
            return render_template("register.html")

        # Validate Email using Regex
        if not re.match(email_regex, email):
            flash("Invalid Email address format!", "error")
            return render_template("register.html")

        # Check if Username already exists in users.csv
        username_exists = False
        if os.path.exists(USERS_CSV):
            with open(USERS_CSV, mode="r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row.get("username") == username:
                        username_exists = True
                        break

        if username_exists:
            flash("Username already exists! Please choose another one.", "error")
            return render_template("register.html")

        # Save new user to users.csv
        with open(USERS_CSV, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([name, mobile, email, username, password])

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login Route: Verifies user credentials against users.csv."""
    initialize_csv_files()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user_found = False
        user_name = ""
        if os.path.exists(USERS_CSV):
            with open(USERS_CSV, mode="r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row.get("username") == username and row.get("password") == password:
                        user_found = True
                        user_name = row.get("name", username)
                        break

        if user_found:
            session["username"] = username
            session["name"] = user_name
            flash("Login successful!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid Username or Password!", "error")

    return render_template("login.html")


@app.route("/home")
def home():
    """Home Page Route: Accessible only after login."""
    if "username" not in session:
        flash("Please login to access the Home page.", "error")
        return redirect(url_for("login"))

    initialize_csv_files()

    contents_list = []
    if os.path.exists(CONTENTS_CSV):
        with open(CONTENTS_CSV, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                contents_list.append(row)

    return render_template(
        "home.html",
        username=session.get("username"),
        name=session.get("name"),
        contents=contents_list,
    )


@app.route("/add_content", methods=["POST"])
def add_content():
    """Add Content Route: Appends new content details into contents.csv."""
    if "username" not in session:
        return redirect(url_for("login"))

    initialize_csv_files()

    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    if title and content:
        with open(CONTENTS_CSV, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([session["username"], title, content])
        flash("Content added successfully!", "success")

    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    """Logout Route: Clears user session."""
    session.clear()
    flash("You have logged out.", "info")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
