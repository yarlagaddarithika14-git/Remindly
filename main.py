
import customtkinter as ctk
import sqlite3
import hashlib
import os
import shutil
import random

from pathlib import Path
from datetime import datetime, timedelta
from tkinter import filedialog
from tkcalendar import Calendar
from PIL import Image, ImageSequence


# =====================================================
# REMINDLY | PREMIUM EDITION
# =====================================================

ctk.set_appearance_mode("light")

app = ctk.CTk()
app.title("Remindly | Your Personal Space")
app.geometry("1200x780")
app.minsize(1000, 680)

# ---------------- PREMIUM COLOURS ----------------

BG = "#F5F3EE"
WHITE = "#FFFFFF"
FOREST = "#34443D"
FOREST_LIGHT = "#52665A"
GOLD = "#B49A70"
SAGE = "#DCE4DC"
TEXT = "#303832"
MUTED = "#899087"
BORDER = "#E9E6DE"
BLUSH = "#F0E3DF"
RED = "#B86F6A"

app.configure(fg_color=BG)

# ---------------- FILES ----------------

BASE = Path(__file__).resolve().parent
AVATAR_FOLDER = BASE / "avatars"
AVATAR_FOLDER.mkdir(exist_ok=True)

# ---------------- DATABASE ----------------

db = sqlite3.connect(BASE / "remindly.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT,
    salt TEXT,
    avatar TEXT DEFAULT '🌿',
    avatar_path TEXT DEFAULT ''
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    task_date TEXT,
    task_time TEXT,
    priority TEXT,
    completed INTEGER DEFAULT 0,
    reminder_sent INTEGER DEFAULT 0
)
""")

# Database compatibility with previous version

user_columns = [
    row[1] for row in cursor.execute(
        "PRAGMA table_info(users)"
    ).fetchall()
]

if "avatar" not in user_columns:
    cursor.execute(
        "ALTER TABLE users ADD COLUMN avatar TEXT DEFAULT '🌿'"
    )

if "avatar_path" not in user_columns:
    cursor.execute(
        "ALTER TABLE users ADD COLUMN avatar_path TEXT DEFAULT ''"
    )

db.commit()

# ---------------- GLOBAL VARIABLES ----------------

current_user = None
current_username = ""
current_avatar = "🌿"
current_avatar_path = ""

avatar_label = None
avatar_frames = []
avatar_index = 0
avatar_job = None
reminder_job = None
task_container = None
stats_container = None
progress_label = None
progress_bar = None
active_filter = "All"


# =====================================================
# GENERAL HELPERS
# =====================================================

def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        200000
    ).hex()


def clear_screen():
    global avatar_label, task_container
    global stats_container, progress_label, progress_bar
    global avatar_job

    if avatar_job:
        app.after_cancel(avatar_job)
        avatar_job = None

    for widget in app.winfo_children():
        widget.destroy()

    avatar_label = None
    task_container = None
    stats_container = None
    progress_label = None
    progress_bar = None


def greeting():
    hour = datetime.now().hour

    if hour < 12:
        return "Good morning"

    if hour < 17:
        return "Good afternoon"

    return "Good evening"


def cute_message(kind):

    messages = {
        "add": [
            "Added, bud! You've got this! ♡",
            "One more thing organised!",
            "Look at you being productive!",
            "Your future self says thank you!",
            "Little steps, big progress!"
        ],

        "complete": [
            "YAYYY! You did it! So proud of you!",
            "Another task conquered!",
            "Look at you go, superstar!",
            "You deserve a little celebration!",
            "Proud of you, bud!"
        ],

        "reminder": [
            "Bud, you gotta do this! Don't forget!",
            "Hey superstar, your task is coming up!",
            "A little reminder just for you!",
            "Time to get this done, bud!",
            "You've got this! Don't forget!"
        ]
    }

    return random.choice(messages[kind])


def make_label(parent, text, size=14, color=TEXT,
               weight="normal", font="Arial"):

    return ctk.CTkLabel(
        parent,
        text=text,
        font=(font, size, weight),
        text_color=color
    )


def make_button(parent, text, command,
                color=FOREST, hover=FOREST_LIGHT,
                width=150, height=42):

    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        height=height,
        corner_radius=10,
        fg_color=color,
        hover_color=hover,
        text_color=WHITE,
        font=("Arial", 13, "bold")
    )


def popup(title, message):

    window = ctk.CTkToplevel(app)
    window.title(title)
    window.geometry("360x190")
    window.configure(fg_color=BG)
    window.transient(app)
    window.grab_set()

    make_label(
        window, title, 23, FOREST, "bold", "Georgia"
    ).pack(pady=(28, 12))

    make_label(
        window, message, 14, MUTED
    ).pack(padx=20, pady=5)

    make_button(
        window, "Continue", window.destroy,
        width=130
    ).pack(pady=20)


def section_heading(parent, title, subtitle=""):

    make_label(
        parent, title, 28, FOREST, "bold", "Georgia"
    ).pack(anchor="w")

    if subtitle:
        make_label(
            parent, subtitle, 13, MUTED
        ).pack(anchor="w", pady=(5, 0))


# =====================================================
# LOGIN
# =====================================================

def show_login():

    clear_screen()

    outer = ctk.CTkFrame(
        app, fg_color=BG
    )
    outer.pack(fill="both", expand=True)

    card = ctk.CTkFrame(
        outer,
        fg_color=WHITE,
        corner_radius=24,
        width=440,
        height=520,
        border_width=1,
        border_color=BORDER
    )
    card.place(relx=0.5, rely=0.5, anchor="center")
    card.pack_propagate(False)

    make_label(
        card, "RE MINDLY", 13, GOLD, "bold"
    ).pack(pady=(45, 12))

    make_label(
        card, "Welcome back.", 32,
        FOREST, "bold", "Georgia"
    ).pack(pady=5)

    make_label(
        card,
        "A little space for your everyday goals.",
        13, MUTED
    ).pack(pady=(0, 28))

    username = ctk.CTkEntry(
        card,
        placeholder_text="Username",
        width=325,
        height=46,
        corner_radius=10,
        border_color=BORDER,
        fg_color=BG,
        text_color=TEXT
    )
    username.pack(pady=10)

    password = ctk.CTkEntry(
        card,
        placeholder_text="Password",
        show="*",
        width=325,
        height=46,
        corner_radius=10,
        border_color=BORDER,
        fg_color=BG,
        text_color=TEXT
    )
    password.pack(pady=10)

    message = make_label(card, "", 12, RED)
    message.pack(pady=5)

    def login():

        global current_user, current_username
        global current_avatar, current_avatar_path

        name = username.get().strip()
        pw = password.get()

        cursor.execute(
            """
            SELECT id, password_hash, salt, avatar, avatar_path
            FROM users WHERE username=?
            """,
            (name,)
        )

        result = cursor.fetchone()

        if not result:
            message.configure(
                text="Account not found. Please sign up."
            )
            return

        user_id, saved_hash, salt, avatar, avatar_path = result

        entered_hash = hash_password(
            pw, bytes.fromhex(salt)
        )

        if entered_hash != saved_hash:
            message.configure(
                text="Incorrect password. Try again."
            )
            return

        current_user = user_id
        current_username = name
        current_avatar = avatar or "🌿"
        current_avatar_path = avatar_path or ""

        show_dashboard()

    make_button(
        card, "LOGIN", login, width=325, height=47
    ).pack(pady=18)

    ctk.CTkButton(
        card,
        text="New to Remindly? Create an account",
        fg_color="transparent",
        hover_color=BG,
        text_color=FOREST_LIGHT,
        command=show_signup
    ).pack(pady=10)


# =====================================================
# SIGNUP
# =====================================================

def show_signup():

    clear_screen()

    outer = ctk.CTkFrame(app, fg_color=BG)
    outer.pack(fill="both", expand=True)

    card = ctk.CTkFrame(
        outer,
        fg_color=WHITE,
        corner_radius=24,
        width=460,
        height=610,
        border_width=1,
        border_color=BORDER
    )
    card.place(relx=0.5, rely=0.5, anchor="center")
    card.pack_propagate(False)

    make_label(
        card, "RE MINDLY", 13, GOLD, "bold"
    ).pack(pady=(28, 8))

    make_label(
        card, "Create your account", 28,
        FOREST, "bold", "Georgia"
    ).pack(pady=5)

    make_label(
        card, "Your organised life starts here.",
        13, MUTED
    ).pack(pady=(0, 15))

    entries = []

    for placeholder, secret in [
        ("Choose a username", False),
        ("Email address", False),
        ("Create password", True),
        ("Confirm password", True)
    ]:

        entry = ctk.CTkEntry(
            card,
            placeholder_text=placeholder,
            show="*" if secret else "",
            width=340,
            height=43,
            corner_radius=10,
            border_color=BORDER,
            fg_color=BG,
            text_color=TEXT
        )
        entry.pack(pady=7)
        entries.append(entry)

    username, email, password, confirm = entries

    message = make_label(card, "", 12, RED)
    message.pack(pady=5)

    def signup():

        name = username.get().strip()
        mail = email.get().strip()
        pw = password.get()

        if not all([
            name, mail, pw, confirm.get()
        ]):
            message.configure(
                text="Please fill in all fields."
            )
            return

        if "@" not in mail or "." not in mail:
            message.configure(
                text="Enter a valid email address."
            )
            return

        if len(pw) < 8:
            message.configure(
                text="Password needs at least 8 characters."
            )
            return

        if pw != confirm.get():
            message.configure(
                text="Passwords do not match."
            )
            return

        salt = os.urandom(16)
        password_hash = hash_password(pw, salt)

        try:
            cursor.execute(
                """
                INSERT INTO users
                (username, email, password_hash, salt)
                VALUES (?, ?, ?, ?)
                """,
                (name, mail, password_hash, salt.hex())
            )

            db.commit()

            message.configure(
                text="Account created successfully!",
                text_color=FOREST_LIGHT
            )

            app.after(1000, show_login)

        except sqlite3.IntegrityError:
            message.configure(
                text="Username or email already exists."
            )

    make_button(
        card, "CREATE ACCOUNT", signup,
        width=340, height=45
    ).pack(pady=15)

    ctk.CTkButton(
        card,
        text="Already registered? Login",
        fg_color="transparent",
        hover_color=BG,
        text_color=FOREST_LIGHT,
        command=show_login
    ).pack(pady=5)


# =====================================================
# AVATAR
# =====================================================

def save_avatar(avatar, path=""):

    global current_avatar, current_avatar_path

    current_avatar = avatar
    current_avatar_path = path

    cursor.execute(
        """
        UPDATE users
        SET avatar=?, avatar_path=?
        WHERE id=?
        """,
        (avatar, path, current_user)
    )

    db.commit()
    update_avatar()


def animate_avatar():

    global avatar_index, avatar_job

    if not avatar_frames or avatar_label is None:
        return

    try:

        frame = avatar_frames[avatar_index]

        photo = ctk.CTkImage(
            light_image=frame,
            dark_image=frame,
            size=(65, 65)
        )

        avatar_label.configure(image=photo, text="")
        avatar_label.image = photo

        avatar_index = (
            avatar_index + 1
        ) % len(avatar_frames)

        avatar_job = app.after(120, animate_avatar)

    except Exception:
        pass


def update_avatar():

    global avatar_frames, avatar_index, avatar_job

    if avatar_label is None:
        return

    if avatar_job:
        app.after_cancel(avatar_job)
        avatar_job = None

    avatar_frames = []
    avatar_index = 0

    if current_avatar_path and os.path.exists(current_avatar_path):

        try:

            image = Image.open(current_avatar_path)

            if getattr(image, "is_animated", False):

                for frame in ImageSequence.Iterator(image):
                    avatar_frames.append(
                        frame.convert("RGBA").copy()
                    )

            else:
                avatar_frames.append(
                    image.convert("RGBA")
                )

            if avatar_frames:
                animate_avatar()
                return

        except Exception:
            pass

    avatar_label.configure(
        image=None,
        text=current_avatar or "🌿",
        font=("Arial", 38)
    )


def choose_avatar():

    window = ctk.CTkToplevel(app)
    window.title("Profile")
    window.geometry("390x330")
    window.configure(fg_color=BG)
    window.transient(app)
    window.grab_set()

    make_label(
        window, "Choose your avatar", 23,
        FOREST, "bold", "Georgia"
    ).pack(pady=25)

    grid = ctk.CTkFrame(window, fg_color=BG)
    grid.pack(pady=10)

    avatars = ["🌿", "🌷", "🐻", "🐰",
               "🐱", "🦋", "🐼", "🧸"]

    for i, avatar in enumerate(avatars):

        ctk.CTkButton(
            grid,
            text=avatar,
            width=65,
            height=55,
            fg_color=WHITE,
            hover_color=SAGE,
            text_color=TEXT,
            font=("Arial", 26),
            command=lambda a=avatar: (
                save_avatar(a),
                window.destroy()
            )
        ).grid(
            row=i // 4,
            column=i % 4,
            padx=6,
            pady=6
        )

    make_button(
        window, "Upload image or GIF",
        lambda: (upload_avatar(), window.destroy()),
        width=200
    ).pack(pady=12)


def upload_avatar():

    path = filedialog.askopenfilename(
        filetypes=[
            ("Image files", "*.png *.jpg *.jpeg *.gif")
        ]
    )

    if not path:
        return

    try:

        extension = Path(path).suffix.lower()

        destination = AVATAR_FOLDER / (
            str(current_user) + extension
        )

        shutil.copy2(path, destination)

        save_avatar("", str(destination))

    except Exception as error:
        popup("Upload error", str(error))


# =====================================================
# DASHBOARD
# =====================================================

def show_dashboard():

    global avatar_label, task_container
    global stats_container, progress_label, progress_bar

    clear_screen()

    main = ctk.CTkFrame(app, fg_color=BG)
    main.pack(fill="both", expand=True)

    # ---------------- SIDEBAR ----------------

    sidebar = ctk.CTkFrame(
        main,
        width=245,
        fg_color=WHITE,
        corner_radius=0
    )
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    make_label(
        sidebar, "RE MINDLY", 21,
        FOREST, "bold", "Georgia"
    ).pack(pady=(38, 35))

    avatar_label = ctk.CTkLabel(
        sidebar,
        text=current_avatar,
        width=85,
        height=85,
        fg_color=BG,
        corner_radius=45,
        font=("Arial", 38)
    )
    avatar_label.pack(pady=5)

    update_avatar()

    make_label(
        sidebar, current_username, 15,
        FOREST, "bold"
    ).pack(pady=10)

    ctk.CTkButton(
        sidebar,
        text="Edit profile",
        fg_color="transparent",
        hover_color=BG,
        text_color=GOLD,
        command=choose_avatar
    ).pack(pady=3)

    make_label(
        sidebar, "WORKSPACE", 11,
        MUTED, "bold"
    ).pack(anchor="w", padx=25, pady=(50, 15))

    nav_buttons = [
        ("▦     Overview", refresh_dashboard),
        ("✓     My tasks", refresh_tasks),
        ("＋     New task", add_task)
    ]

    for label, command in nav_buttons:

        ctk.CTkButton(
            sidebar,
            text=label,
            anchor="w",
            height=44,
            fg_color=BG if label.startswith("▦") else WHITE,
            hover_color=BG,
            text_color=FOREST,
            corner_radius=9,
            command=command
        ).pack(fill="x", padx=16, pady=4)

    make_label(
        sidebar,
        "Make time for what matters.",
        12, MUTED
    ).pack(side="bottom", pady=(10, 18))

    ctk.CTkButton(
        sidebar,
        text="Log out",
        fg_color=BLUSH,
        hover_color="#E7D5CF",
        text_color=FOREST,
        height=42,
        corner_radius=10,
        command=logout
    ).pack(side="bottom", fill="x", padx=17, pady=12)

    # ---------------- CONTENT ----------------

    content = ctk.CTkFrame(main, fg_color=BG)
    content.pack(
        side="left",
        fill="both",
        expand=True,
        padx=35,
        pady=30
    )

    top = ctk.CTkFrame(content, fg_color=BG)
    top.pack(fill="x")

    left = ctk.CTkFrame(top, fg_color=BG)
    left.pack(side="left", fill="x", expand=True)

    section_heading(
        left,
        greeting() + ", " + current_username + ".",
        "A little progress every day adds up."
    )

    make_label(
        top,
        datetime.now().strftime("%A, %d %B %Y"),
        13, MUTED
    ).pack(side="right", anchor="n", pady=10)

    # ---------------- STATISTICS ----------------

    stats_container = ctk.CTkFrame(
        content,
        fg_color=BG
    )
    stats_container.pack(fill="x", pady=(28, 10))

    # ---------------- PROGRESS ----------------

    progress_card = ctk.CTkFrame(
        content,
        fg_color=FOREST,
        corner_radius=16,
        height=115
    )
    progress_card.pack(fill="x", pady=10)
    progress_card.pack_propagate(False)

    make_label(
        progress_card,
        "YOUR DAILY PROGRESS",
        11, "#D8C9A9", "bold"
    ).pack(anchor="w", padx=22, pady=(17, 5))

    progress_label = make_label(
        progress_card,
        "Keep going. You're doing great.",
        14, WHITE
    )
    progress_label.pack(anchor="w", padx=22, pady=2)

    progress_bar = ctk.CTkProgressBar(
        progress_card,
        width=350,
        height=9,
        progress_color="#D8C9A9",
        fg_color="#64766A"
    )
    progress_bar.pack(anchor="w", padx=22, pady=9)

    # ---------------- TASK HEADER ----------------

    task_header = ctk.CTkFrame(
        content, fg_color=BG
    )
    task_header.pack(fill="x", pady=(25, 10))

    make_label(
        task_header, "Your tasks", 23,
        FOREST, "bold", "Georgia"
    ).pack(side="left")

    make_button(
        task_header, "+ Add task", add_task,
        width=130, height=39
    ).pack(side="right")

    # ---------------- FILTER ----------------

    filter_row = ctk.CTkFrame(content, fg_color=BG)
    filter_row.pack(fill="x", pady=5)

    filter_menu = ctk.CTkSegmentedButton(
        filter_row,
        values=["All", "Pending", "Completed"],
        selected_color=FOREST,
        selected_hover_color=FOREST_LIGHT,
        unselected_color=WHITE,
        unselected_hover_color=SAGE,
        text_color=TEXT,
        command=change_filter
    )
    filter_menu.pack(anchor="w")
    filter_menu.set(active_filter)

    # ---------------- TASK LIST ----------------

    task_container = ctk.CTkScrollableFrame(
        content,
        fg_color=BG,
        scrollbar_button_color=GOLD
    )
    task_container.pack(fill="both", expand=True, pady=8)

    refresh_dashboard()


def refresh_dashboard():

    if stats_container is None:
        return

    for widget in stats_container.winfo_children():
        widget.destroy()

    cursor.execute(
        """
        SELECT COUNT(*),
        SUM(CASE WHEN completed=1 THEN 1 ELSE 0 END)
        FROM tasks WHERE user_id=?
        """,
        (current_user,)
    )

    total, completed = cursor.fetchone()

    total = total or 0
    completed = completed or 0
    pending = total - completed

    stats = [
        ("TOTAL TASKS", total, GOLD),
        ("COMPLETED", completed, FOREST_LIGHT),
        ("PENDING", pending, "#B98276")
    ]

    for title, value, color in stats:

        card = ctk.CTkFrame(
            stats_container,
            fg_color=WHITE,
            corner_radius=13,
            border_width=1,
            border_color=BORDER
        )
        card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 12)
        )

        make_label(
            card, title, 10, MUTED, "bold"
        ).pack(anchor="w", padx=17, pady=(15, 4))

        make_label(
            card, str(value), 27, color,
            "bold", "Georgia"
        ).pack(anchor="w", padx=17, pady=(0, 14))

    percentage = completed / total if total else 0

    if progress_bar:
        progress_bar.set(percentage)

    if progress_label:
        progress_label.configure(
            text=f"{completed} of {total} tasks completed. Keep it up!"
        )


# =====================================================
# TASK FILTERS AND TASK LIST
# =====================================================

def change_filter(value):

    global active_filter

    active_filter = value
    refresh_tasks()


def refresh_tasks():

    if task_container is None:
        return

    for widget in task_container.winfo_children():
        widget.destroy()

    query = """
        SELECT id, name, task_date, task_time, priority, completed
        FROM tasks
        WHERE user_id=?
    """

    if active_filter == "Pending":
        query += " AND completed=0"

    elif active_filter == "Completed":
        query += " AND completed=1"

    query += " ORDER BY completed ASC, task_date ASC, task_time ASC"

    cursor.execute(query, (current_user,))
    tasks = cursor.fetchall()

    if not tasks:

        message = {
            "All": "Your space is clear. Add your first task.",
            "Pending": "No pending tasks. Lovely work!",
            "Completed": "Your completed tasks will appear here."
        }

        make_label(
            task_container,
            message[active_filter],
            15, MUTED
        ).pack(pady=45)

        return

    for task in tasks:

        task_id, name, date, time, priority, completed = task

        card = ctk.CTkFrame(
            task_container,
            fg_color=WHITE,
            corner_radius=13,
            border_width=1,
            border_color=BORDER
        )
        card.pack(fill="x", pady=6, padx=2)

        priority_colors = {
            "High": "#B98276",
            "Medium": GOLD,
            "Low": FOREST_LIGHT
        }

        stripe = ctk.CTkFrame(
            card,
            width=5,
            fg_color=priority_colors.get(priority, GOLD),
            corner_radius=4
        )
        stripe.pack(side="left", fill="y", padx=(0, 12))

        details = ctk.CTkFrame(
            card, fg_color=WHITE
        )
        details.pack(
            side="left",
            fill="x",
            expand=True,
            padx=5,
            pady=13
        )

        title = name

        if completed:
            title = "✓  " + name

        make_label(
            details,
            title,
            15,
            MUTED if completed else FOREST,
            "bold"
        ).pack(anchor="w")

        make_label(
            details,
            f"{date}  •  {time}",
            12, MUTED
        ).pack(anchor="w", pady=(5, 0))

        badge = ctk.CTkLabel(
            card,
            text=priority.upper(),
            fg_color=BG,
            text_color=priority_colors.get(priority, GOLD),
            corner_radius=7,
            font=("Arial", 10, "bold"),
            width=75,
            height=27
        )
        badge.pack(side="left", padx=8)

        actions = ctk.CTkFrame(
            card, fg_color=WHITE
        )
        actions.pack(side="right", padx=12)

        if not completed:

            ctk.CTkButton(
                actions,
                text="✓",
                width=34,
                height=32,
                fg_color=SAGE,
                hover_color="#C7D5C7",
                text_color=FOREST,
                command=lambda i=task_id: complete_task(i)
            ).pack(side="left", padx=3)

            ctk.CTkButton(
                actions,
                text="Edit",
                width=48,
                height=32,
                fg_color=BG,
                hover_color=SAGE,
                text_color=FOREST,
                command=lambda i=task_id: edit_task(i)
            ).pack(side="left", padx=3)

        ctk.CTkButton(
            actions,
            text="×",
            width=32,
            height=32,
            fg_color=BLUSH,
            hover_color="#E7D5CF",
            text_color=FOREST,
            command=lambda i=task_id: delete_task(i)
        ).pack(side="left", padx=3)


def update_task_display():

    refresh_dashboard()
    refresh_tasks()


def complete_task(task_id):

    cursor.execute(
        """
        UPDATE tasks SET completed=1
        WHERE id=? AND user_id=?
        """,
        (task_id, current_user)
    )

    db.commit()
    update_task_display()

    popup(
        "Well done!",
        cute_message("complete")
    )


def delete_task(task_id):

    cursor.execute(
        """
        DELETE FROM tasks
        WHERE id=? AND user_id=?
        """,
        (task_id, current_user)
    )

    db.commit()
    update_task_display()


# =====================================================
# CALENDAR
# =====================================================

def choose_date(entry):

    window = ctk.CTkToplevel(app)
    window.title("Select date")
    window.geometry("350x360")
    window.configure(fg_color=BG)
    window.transient(app)
    window.grab_set()

    calendar = Calendar(
        window,
        selectmode="day",
        date_pattern="yyyy-mm-dd",
        background=FOREST,
        foreground=WHITE,
        headersbackground=FOREST_LIGHT,
        headersforeground=WHITE,
        selectbackground=GOLD,
        normalbackground=WHITE,
        normalforeground=TEXT
    )

    calendar.pack(
        padx=15, pady=20,
        fill="both", expand=True
    )

    def select():

        entry.delete(0, "end")
        entry.insert(0, calendar.get_date())
        window.destroy()

    make_button(
        window, "Confirm date",
        select, width=150
    ).pack(pady=12)


# =====================================================
# ADD AND EDIT TASK
# =====================================================

def add_task():
    task_form()


def edit_task(task_id):

    cursor.execute(
        """
        SELECT name, task_date, task_time, priority
        FROM tasks
        WHERE id=? AND user_id=?
        """,
        (task_id, current_user)
    )

    old_task = cursor.fetchone()

    if old_task:
        task_form(task_id, old_task)


def task_form(task_id=None, old_task=None):

    window = ctk.CTkToplevel(app)
    window.title("Remindly | Task")
    window.geometry("480x620")
    window.configure(fg_color=BG)
    window.transient(app)
    window.grab_set()

    section_heading(
        window,
        "Edit task" if task_id else "A new task.",
        "Give your next little goal a place."
    )

    name = ctk.CTkEntry(
        window,
        placeholder_text="Task name",
        width=340,
        height=44,
        fg_color=WHITE,
        border_color=BORDER,
        text_color=TEXT
    )
    name.pack(pady=12)

    if old_task:
        name.insert(0, old_task[0])

    make_label(
        window, "DATE", 11, MUTED, "bold"
    ).pack(pady=(13, 5))

    date_row = ctk.CTkFrame(window, fg_color=BG)
    date_row.pack()

    date = ctk.CTkEntry(
        date_row,
        width=240,
        height=42,
        fg_color=WHITE,
        border_color=BORDER,
        text_color=TEXT
    )
    date.pack(side="left", padx=5)

    date.insert(
        0,
        old_task[1] if old_task else
        datetime.now().strftime("%Y-%m-%d")
    )

    make_button(
        date_row, "Calendar",
        lambda: choose_date(date),
        width=90
    ).pack(side="left", padx=5)

    make_label(
        window, "TIME (24-HOUR FORMAT)", 11,
        MUTED, "bold"
    ).pack(pady=(16, 5))

    time = ctk.CTkEntry(
        window,
        placeholder_text="HH:MM e.g. 14:30",
        width=340,
        height=42,
        fg_color=WHITE,
        border_color=BORDER,
        text_color=TEXT
    )
    time.pack()

    if old_task:
        time.insert(0, old_task[2])

    make_label(
        window, "PRIORITY", 11, MUTED, "bold"
    ).pack(pady=(18, 5))

    priority = ctk.CTkOptionMenu(
        window,
        values=["Low", "Medium", "High"],
        fg_color=FOREST,
        button_color=FOREST_LIGHT,
        button_hover_color=FOREST_LIGHT,
        width=200
    )
    priority.pack()

    if old_task:
        priority.set(old_task[3])
    else:
        priority.set("Medium")

    message = make_label(window, "", 12, RED)
    message.pack(pady=12)

    def save():

        task_name = name.get().strip()
        task_date = date.get().strip()
        task_time = time.get().strip()
        task_priority = priority.get()

        if not task_name or not task_date or not task_time:
            message.configure(
                text="Please fill in all the details."
            )
            return

        try:

            due = datetime.strptime(
                task_date + " " + task_time,
                "%Y-%m-%d %H:%M"
            )

            if due <= datetime.now():
                message.configure(
                    text="Please select a future date and time."
                )
                return

        except ValueError:

            message.configure(
                text="Check your date and time format."
            )
            return

        if task_id:

            cursor.execute(
                """
                UPDATE tasks
                SET name=?, task_date=?, task_time=?,
                    priority=?, reminder_sent=0
                WHERE id=? AND user_id=?
                """,
                (
                    task_name, task_date, task_time,
                    task_priority, task_id, current_user
                )
            )

        else:

            cursor.execute(
                """
                INSERT INTO tasks
                (user_id, name, task_date, task_time, priority)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    current_user, task_name,
                    task_date, task_time, task_priority
                )
            )

        db.commit()
        window.destroy()

        update_task_display()

        if not task_id:
            popup(
                "Task added",
                cute_message("add")
            )

    make_button(
        window,
        "SAVE TASK",
        save,
        width=340,
        height=46
    ).pack(pady=12)


# =====================================================
# REMINDERS
# =====================================================

def check_reminders():

    global reminder_job

    if current_user is None:
        return

    now = datetime.now()

    cursor.execute(
        """
        SELECT id, name, task_date, task_time
        FROM tasks
        WHERE user_id=?
        AND completed=0
        AND reminder_sent=0
        """,
        (current_user,)
    )

    tasks = cursor.fetchall()

    for task in tasks:

        task_id, name, date, time = task

        try:

            due = datetime.strptime(
                date + " " + time,
                "%Y-%m-%d %H:%M"
            )

            reminder = due - timedelta(hours=1)

            if reminder <= now < due:

                cursor.execute(
                    """
                    UPDATE tasks
                    SET reminder_sent=1
                    WHERE id=?
                    """,
                    (task_id,)
                )

                db.commit()

                popup(
                    "A little reminder",
                    name + "\n\n" + cute_message("reminder")
                )

        except ValueError:
            pass

    reminder_job = app.after(30000, check_reminders)


# =====================================================
# LOGOUT AND CLOSE
# =====================================================

def logout():

    global current_user, current_username
    global current_avatar, current_avatar_path
    global reminder_job

    if reminder_job:
        app.after_cancel(reminder_job)
        reminder_job = None

    current_user = None
    current_username = ""
    current_avatar = "🌿"
    current_avatar_path = ""

    show_login()


def close_app():

    global reminder_job, avatar_job

    if reminder_job:
        app.after_cancel(reminder_job)

    if avatar_job:
        app.after_cancel(avatar_job)

    db.commit()
    db.close()
    app.destroy()


# =====================================================
# START
# =====================================================

app.protocol("WM_DELETE_WINDOW", close_app)

show_login()

app.mainloop()
