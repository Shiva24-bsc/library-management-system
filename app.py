from datetime import date, timedelta

from flask import Flask, flash, redirect, render_template, request, session

from config import db

app = Flask(__name__)
app.secret_key = "secret123"

# Simple fine rule used across the whole system.
FINE_PER_DAY = 1


def get_cursor(dictionary=False):
    # Reconnect if MySQL dropped the connection, which can happen during longer sessions.
    db.ping(reconnect=True, attempts=3, delay=2)
    return db.cursor(dictionary=dictionary)


def ensure_schema():
    cursor = get_cursor()

    # This helps the dashboard show newly added books in the new arrivals section.
    cursor.execute("SHOW COLUMNS FROM books LIKE 'created_at'")
    if not cursor.fetchone():
        cursor.execute(
            """
            ALTER TABLE books
            ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """
        )

    # Cover image links make the catalogue look more realistic and visual.
    cursor.execute("SHOW COLUMNS FROM books LIKE 'cover_url'")
    if not cursor.fetchone():
        cursor.execute(
            """
            ALTER TABLE books
            ADD COLUMN cover_url VARCHAR(500) NULL AFTER category
            """
        )

    # Due dates are required for reminders, overdue tracking, and fine calculation.
    cursor.execute("SHOW COLUMNS FROM borrow LIKE 'due_date'")
    if not cursor.fetchone():
        cursor.execute(
            """
            ALTER TABLE borrow
            ADD COLUMN due_date DATE NULL AFTER borrow_date
            """
        )

    # returned_at separates active borrowing from completed returns more clearly.
    cursor.execute("SHOW COLUMNS FROM borrow LIKE 'returned_at'")
    if not cursor.fetchone():
        cursor.execute(
            """
            ALTER TABLE borrow
            ADD COLUMN returned_at DATE NULL AFTER due_date
            """
        )

    # These fields make the fine system behave more like a real system instead of only showing a visual amount.
    cursor.execute("SHOW COLUMNS FROM borrow LIKE 'fine_paid'")
    if not cursor.fetchone():
        cursor.execute(
            """
            ALTER TABLE borrow
            ADD COLUMN fine_paid TINYINT(1) DEFAULT 0 AFTER returned_at
            """
        )

    cursor.execute("SHOW COLUMNS FROM borrow LIKE 'fine_paid_at'")
    if not cursor.fetchone():
        cursor.execute(
            """
            ALTER TABLE borrow
            ADD COLUMN fine_paid_at DATE NULL AFTER fine_paid
            """
        )

    # created_at on users lets the admin dashboard show recent registrations naturally.
    cursor.execute("SHOW COLUMNS FROM users LIKE 'created_at'")
    if not cursor.fetchone():
        cursor.execute(
            """
            ALTER TABLE users
            ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """
        )

    # Backfill due dates for any older rows that were created before the due_date column existed.
    cursor.execute(
        """
        UPDATE borrow
        SET due_date = DATE_ADD(borrow_date, INTERVAL 14 DAY)
        WHERE due_date IS NULL AND borrow_date IS NOT NULL
        """
    )

    # Backfill returned_at from the older return_date field if needed.
    cursor.execute(
        """
        UPDATE borrow
        SET returned_at = return_date
        WHERE returned_at IS NULL AND return_date IS NOT NULL
        """
    )

    db.commit()
    cursor.close()


def login_required():
    # A very simple session check used before protected pages are loaded.
    return "user" in session


def hydrate_session_user():
    if "user" not in session:
        return False

    # We use user_id here so the system refreshes the exact user's role reliably.
    if "user_id" not in session:
        return False

    # If the role is already in session, there is nothing extra to refresh.
    if "role" in session:
        return True

    cursor = get_cursor(dictionary=True)
    cursor.execute(
        "SELECT user_id, role FROM users WHERE user_id = %s LIMIT 1",
        (session["user_id"],),
    )
    user = cursor.fetchone()
    cursor.close()

    # If the user no longer exists, clear the session so the app does not keep stale login data.
    if not user:
        session.clear()
        return False

    session["role"] = user.get("role", "user")
    return True


def is_admin():
    # Central helper used whenever admin-only actions are checked.
    return session.get("role") == "admin"


def calculate_overdue_days(due_date_value, returned_at_value=None):
    # If there is no due date, there is no overdue calculation to make.
    if not due_date_value:
        return 0

    # For returned books we compare against the return date.
    # For active books we compare against today's date.
    reference_date = returned_at_value if returned_at_value else date.today()
    overdue_days = (reference_date - due_date_value).days
    return max(overdue_days, 0)


def calculate_fine(due_date_value, returned_at_value=None):
    # The fine is intentionally simple: 1 pound per overdue day.
    return calculate_overdue_days(due_date_value, returned_at_value) * FINE_PER_DAY


def days_ago_label(value):
    # This creates small human-friendly labels for the dashboard like "today" or "3 days ago".
    if not value:
        return ""
    diff = (date.today() - value).days
    if diff <= 0:
        return "today"
    if diff == 1:
        return "1 day ago"
    return f"{diff} days ago"


def due_status_label(due_date_value):
    # This helper keeps due-date wording consistent everywhere in the UI.
    if not due_date_value:
        return ("Unknown", "info")

    diff = (due_date_value - date.today()).days

    if diff < 0:
        return (f"Overdue by {abs(diff)} day(s)", "overdue")
    if diff == 0:
        return ("Due today", "warning")
    if diff == 1:
        return ("Due tomorrow", "warning")
    return (f"Due in {diff} days", "borrowed")


def make_notification(title, detail, note_type, icon, timestamp, action_label=None, action_url=None):
    # Keeping notification creation in one helper makes the dashboard code easier to read later.
    return {
        "title": title,
        "detail": detail,
        "type": note_type,
        "icon": icon,
        "timestamp": timestamp,
        "action_label": action_label,
        "action_url": action_url,
        "unread": True,
    }


def fetch_book(book_id):
    # This query returns one book together with live availability details.
    cursor = get_cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
            b.book_id,
            b.title,
            b.author,
            b.category,
            b.cover_url,
            b.quantity,
            COALESCE(active.active_loans, 0) AS active_loans,
            GREATEST(b.quantity - COALESCE(active.active_loans, 0), 0) AS available_quantity
        FROM books b
        LEFT JOIN (
            SELECT book_id, COUNT(*) AS active_loans
            FROM borrow
            WHERE returned_at IS NULL
            GROUP BY book_id
        ) active ON active.book_id = b.book_id
        WHERE b.book_id = %s
        """,
        (book_id,),
    )
    book = cursor.fetchone()
    cursor.close()
    return book


def fetch_books(search_text="", category="", availability=""):
    # This builds the catalogue list together with current available quantity for each book.
    cursor = get_cursor(dictionary=True)
    query = """
        SELECT
            b.book_id,
            b.title,
            b.author,
            b.category,
            b.cover_url,
            b.quantity,
            b.created_at,
            COALESCE(active.active_loans, 0) AS active_loans,
            GREATEST(b.quantity - COALESCE(active.active_loans, 0), 0) AS available_quantity
        FROM books b
        LEFT JOIN (
            SELECT book_id, COUNT(*) AS active_loans
            FROM borrow
            WHERE returned_at IS NULL
            GROUP BY book_id
        ) active ON active.book_id = b.book_id
        WHERE 1 = 1
    """
    params = []

    # Search can match title, author, or category to make browsing easier for users.
    if search_text:
        query += """
            AND (
                b.title LIKE %s
                OR b.author LIKE %s
                OR b.category LIKE %s
            )
        """
        term = f"%{search_text}%"
        params.extend([term, term, term])

    # Category filter narrows the catalogue to one genre or subject.
    if category:
        query += " AND b.category = %s"
        params.append(category)

    # Availability filter helps users quickly find available or fully borrowed books.
    if availability == "available":
        query += " AND GREATEST(b.quantity - COALESCE(active.active_loans, 0), 0) > 0"
    elif availability == "borrowed":
        query += " AND GREATEST(b.quantity - COALESCE(active.active_loans, 0), 0) = 0"

    query += " ORDER BY b.title ASC"

    cursor.execute(query, tuple(params))
    books = cursor.fetchall()
    cursor.close()

    # These status labels are used directly by the books page badges.
    for book in books:
        if book["available_quantity"] <= 0:
            book["status"] = "Borrowed"
            book["status_class"] = "borrowed"
        elif book["available_quantity"] == 1:
            book["status"] = "Low Stock"
            book["status_class"] = "low"
        else:
            book["status"] = "Available"
            book["status_class"] = "available"

    return books


def fetch_categories():
    # Distinct categories are used to populate the search filter dropdown.
    cursor = get_cursor()
    cursor.execute(
        "SELECT DISTINCT category FROM books WHERE category IS NOT NULL AND category <> '' ORDER BY category"
    )
    categories = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return categories


ensure_schema()


@app.route("/")
def home():
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Basic registration fields come directly from the form.
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"].strip()

        # A simple validation step keeps incomplete submissions out of the database.
        if not name or not email or not password:
            return render_template("register.html", error="All fields are required!")

        cursor = get_cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()

        # Email must be unique so each person logs in with one clear account.
        if existing_user:
            cursor.close()
            return render_template("register.html", error="Email already exists!")

        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
            (name, email, password, "user"),
        )
        db.commit()
        cursor.close()

        flash("Registration successful. Please log in.", "success")
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Login is based on email and password.
        email = request.form["email"].strip()
        password = request.form["password"].strip()

        if not email or not password:
            return render_template("login.html", error="Please enter both email and password!")

        cursor = get_cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if not user:
            return render_template("login.html", error="User not found!")

        if user["password"] != password:
            return render_template("login.html", error="Wrong password!")

        # Session stores the current logged-in identity and permissions.
        session["user"] = user["name"]
        session["user_id"] = user["user_id"]
        session["role"] = user.get("role", "user")

        flash("Welcome back. You have logged in successfully.", "success")
        return redirect("/dashboard")

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if not login_required() or not hydrate_session_user():
        return redirect("/login")

    # This controls which notification tab is active.
    notification_filter = request.args.get("notification_filter", "all").strip().lower()
    if notification_filter not in ("all", "unread", "alerts"):
        notification_filter = "all"

    cursor = get_cursor(dictionary=True)

    # These are global system stats used mostly by admins.
    cursor.execute("SELECT COUNT(*) AS total_books FROM books")
    total_books = cursor.fetchone()["total_books"]

    cursor.execute("SELECT COUNT(*) AS total_users FROM users")
    total_users = cursor.fetchone()["total_users"]

    cursor.execute("SELECT COUNT(*) AS active_loans FROM borrow WHERE returned_at IS NULL")
    active_loans = cursor.fetchone()["active_loans"]

    cursor.execute(
        """
        SELECT COUNT(*) AS overdue_count
        FROM borrow
        WHERE returned_at IS NULL AND due_date < CURDATE()
        """
    )
    overdue_count = cursor.fetchone()["overdue_count"]

    # These are personal user stats shown in the user dashboard cards.
    cursor.execute(
        """
        SELECT COUNT(*) AS my_borrowed_books
        FROM borrow
        WHERE user_id = %s AND returned_at IS NULL
        """,
        (session["user_id"],),
    )
    my_borrowed_books = cursor.fetchone()["my_borrowed_books"]

    cursor.execute(
        """
        SELECT COUNT(*) AS my_due_soon
        FROM borrow
        WHERE user_id = %s
          AND returned_at IS NULL
          AND due_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 3 DAY)
        """,
        (session["user_id"],),
    )
    my_due_soon = cursor.fetchone()["my_due_soon"]

    cursor.execute(
        """
        SELECT COUNT(*) AS my_overdue
        FROM borrow
        WHERE user_id = %s
          AND returned_at IS NULL
          AND due_date < CURDATE()
        """,
        (session["user_id"],),
    )
    my_overdue = cursor.fetchone()["my_overdue"]

    cursor.execute(
        """
        SELECT COUNT(*) AS my_returned
        FROM borrow
        WHERE user_id = %s
          AND returned_at IS NOT NULL
        """,
        (session["user_id"],),
    )
    my_returned = cursor.fetchone()["my_returned"]

    # This is the real unpaid total fine for the logged-in user.
    cursor.execute(
        """
        SELECT
            borrow_id,
            due_date,
            returned_at,
            fine_paid
        FROM borrow
        WHERE user_id = %s
        """,
        (session["user_id"],),
    )
    user_fine_rows = cursor.fetchall()

    my_total_fine = 0
    for row in user_fine_rows:
        if row["fine_paid"]:
            continue
        fine_amount = calculate_fine(row["due_date"], row["returned_at"])
        my_total_fine += fine_amount

    # Active borrowed books are shown to the user with return options and due status.
    cursor.execute(
        """
        SELECT
            b.borrow_id,
            bk.title,
            bk.author,
            bk.category,
            bk.cover_url,
            b.borrow_date,
            b.due_date,
            b.fine_paid
        FROM borrow b
        JOIN books bk ON bk.book_id = b.book_id
        WHERE b.user_id = %s AND b.returned_at IS NULL
        ORDER BY b.due_date ASC
        LIMIT 5
        """,
        (session["user_id"],),
    )
    borrowed_now = cursor.fetchall()

    # Reading history lets users see returned books and any unpaid late fine still attached to them.
    cursor.execute(
        """
        SELECT
            b.borrow_id,
            bk.title,
            bk.author,
            bk.cover_url,
            b.borrow_date,
            b.returned_at,
            b.due_date,
            b.fine_paid
        FROM borrow b
        JOIN books bk ON bk.book_id = b.book_id
        WHERE b.user_id = %s AND b.returned_at IS NOT NULL
        ORDER BY b.returned_at DESC
        LIMIT 5
        """,
        (session["user_id"],),
    )
    reading_history = cursor.fetchall()

    # This gives a short recent activity list for the dashboard.
    cursor.execute(
        """
        SELECT
            b.borrow_id,
            bk.title,
            b.borrow_date,
            b.due_date,
            b.returned_at,
            CASE
                WHEN b.returned_at IS NOT NULL THEN 'Returned'
                WHEN b.due_date < CURDATE() THEN 'Overdue'
                ELSE 'Borrowed'
            END AS loan_status
        FROM borrow b
        JOIN books bk ON bk.book_id = b.book_id
        WHERE b.user_id = %s
        ORDER BY
            CASE WHEN b.returned_at IS NULL THEN 0 ELSE 1 END,
            b.borrow_date DESC
        LIMIT 5
        """,
        (session["user_id"],),
    )
    recent_activity = cursor.fetchall()

    # These are used for overdue notifications.
    cursor.execute(
        """
        SELECT
            b.borrow_id,
            bk.title,
            b.due_date
        FROM borrow b
        JOIN books bk ON bk.book_id = b.book_id
        WHERE b.user_id = %s
          AND b.returned_at IS NULL
          AND b.due_date < CURDATE()
        ORDER BY b.due_date ASC
        """,
        (session["user_id"],),
    )
    overdue_books = cursor.fetchall()

    # These are used for due-soon notifications.
    cursor.execute(
        """
        SELECT
            b.borrow_id,
            bk.title,
            b.due_date
        FROM borrow b
        JOIN books bk ON bk.book_id = b.book_id
        WHERE b.user_id = %s
          AND b.returned_at IS NULL
          AND b.due_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 3 DAY)
        ORDER BY b.due_date ASC
        """,
        (session["user_id"],),
    )
    due_soon_books = cursor.fetchall()

    # New arrivals support the dashboard's live library feeling.
    cursor.execute(
        """
        SELECT title, author, category, cover_url, created_at
        FROM books
        ORDER BY created_at DESC
        LIMIT 4
        """
    )
    new_arrivals = cursor.fetchall()

    # Low stock helps the admin monitor books that may need attention.
    cursor.execute(
        """
        SELECT
            b.book_id,
            b.title,
            GREATEST(b.quantity - COALESCE(active.active_loans, 0), 0) AS available_quantity
        FROM books b
        LEFT JOIN (
            SELECT book_id, COUNT(*) AS active_loans
            FROM borrow
            WHERE returned_at IS NULL
            GROUP BY book_id
        ) active ON active.book_id = b.book_id
        HAVING available_quantity <= 1
        ORDER BY available_quantity ASC, b.title ASC
        LIMIT 5
        """
    )
    low_stock_books = cursor.fetchall()

    # Recent registrations are shown in notifications for the admin side.
    cursor.execute(
        """
        SELECT COUNT(*) AS new_users_count
        FROM users
        WHERE DATE(created_at) = CURDATE()
        """
    )
    new_users_count = cursor.fetchone()["new_users_count"]

    # This feeds the registered users table for admin.
    cursor.execute(
        """
        SELECT user_id, name, email, role, created_at
        FROM users
        ORDER BY created_at DESC, user_id DESC
        LIMIT 10
        """
    )
    registered_users = cursor.fetchall()

    # This query feeds the separate admin fine area.
    cursor.execute(
        """
        SELECT
            b.borrow_id,
            u.name,
            u.email,
            bk.title,
            b.due_date,
            b.returned_at,
            b.fine_paid
        FROM borrow b
        JOIN users u ON u.user_id = b.user_id
        JOIN books bk ON bk.book_id = b.book_id
        ORDER BY b.due_date ASC
        """
    )
    raw_admin_fine_rows = cursor.fetchall()

    cursor.close()

    admin_fine_rows = []
    total_system_fine = 0

    # Only unpaid fines are shown in the admin fine area so the list stays realistic and useful.
    for row in raw_admin_fine_rows:
        if row["fine_paid"]:
            continue
        fine_amount = calculate_fine(row["due_date"], row["returned_at"])
        if fine_amount <= 0:
            continue

        row["overdue_days"] = calculate_overdue_days(row["due_date"], row["returned_at"])
        row["fine_amount"] = fine_amount
        admin_fine_rows.append(row)
        total_system_fine += fine_amount

    # Add presentation labels and active fine values to current borrowed books.
    for item in borrowed_now:
        item["borrowed_label"] = days_ago_label(item["borrow_date"])
        status_text, status_class = due_status_label(item["due_date"])
        item["due_status_text"] = status_text
        item["due_status_class"] = status_class
        item["overdue_days"] = calculate_overdue_days(item["due_date"])
        item["fine_amount"] = 0 if item["fine_paid"] else calculate_fine(item["due_date"])

    # Returned books may still show unpaid late fines if they have not been cleared.
    for item in reading_history:
        item["borrowed_label"] = days_ago_label(item["borrow_date"])
        item["returned_fine"] = 0 if item["fine_paid"] else calculate_fine(item["due_date"], item["returned_at"])

    notifications = []

    if is_admin():
        # Admin notifications focus on system monitoring rather than one single user's activity.
        if overdue_count > 0:
            notifications.append(
                make_notification(
                    title=f"{overdue_count} overdue book(s) need attention",
                    detail="Some borrowed books are overdue and should be reviewed by the admin.",
                    note_type="overdue",
                    icon="alert",
                    timestamp="Today",
                    action_label="Check Fine Area",
                    action_url="/dashboard",
                )
            )

        if total_system_fine > 0:
            notifications.append(
                make_notification(
                    title=f"Outstanding fine total: £{total_system_fine}",
                    detail="There are unpaid overdue fines in the system that need admin attention.",
                    note_type="warning",
                    icon="money",
                    timestamp="Today",
                    action_label="View Fine Summary",
                    action_url="/dashboard",
                )
            )

        if new_users_count > 0:
            notifications.append(
                make_notification(
                    title=f"{new_users_count} new user(s) registered today",
                    detail="A new user registration was recorded in the system today.",
                    note_type="info",
                    icon="user",
                    timestamp="Today",
                )
            )

        for book in low_stock_books[:2]:
            notifications.append(
                make_notification(
                    title=f"Low stock: {book['title']}",
                    detail=f"Only {book['available_quantity']} copy/copies available right now.",
                    note_type="warning",
                    icon="stock",
                    timestamp="Today",
                    action_label="Restock Book",
                    action_url=f"/books/edit/{book['book_id']}",
                )
            )
    else:
        # User notifications are based only on that user's real borrowing and fine data.
        if my_total_fine > 0:
            notifications.append(
                make_notification(
                    title=f"Current unpaid fine: £{my_total_fine}",
                    detail="You currently have unpaid overdue fines in your account.",
                    note_type="overdue",
                    icon="money",
                    timestamp="Today",
                    action_label="View My Books",
                    action_url="/dashboard",
                )
            )

        if my_due_soon > 0:
            notifications.append(
                make_notification(
                    title=f"{my_due_soon} book(s) due soon",
                    detail="One or more of your borrowed books will be due very soon.",
                    note_type="warning",
                    icon="clock",
                    timestamp="Today",
                    action_label="Check Due Dates",
                    action_url="/dashboard",
                )
            )

        # This keeps due-soon alerts readable instead of listing too many separate cards.
        if my_due_soon > 0 and due_soon_books:
            due_titles = ", ".join(item["title"] for item in due_soon_books[:2])
            notifications.append(
                make_notification(
                    title="Books due soon",
                    detail=f"These books are close to the return date: {due_titles}.",
                    note_type="warning",
                    icon="book",
                    timestamp="Today",
                    action_label="Manage Borrowing",
                    action_url="/books",
                )
            )

        for item in overdue_books[:2]:
            fine_amount = calculate_fine(item["due_date"])
            overdue_days = calculate_overdue_days(item["due_date"])
            notifications.append(
                make_notification(
                    title=f"{item['title']} is overdue",
                    detail=f"Overdue by {overdue_days} day(s). Current fine: £{fine_amount}.",
                    note_type="warning",
                    icon="alert",
                    timestamp="Today",
                    action_label="Return Book",
                    action_url="/dashboard",
                )
            )

        for item in new_arrivals[:2]:
            notifications.append(
                make_notification(
                    title=f"New book added: {item['title']}",
                    detail=f"Recently added in {item['category']} by {item['author']}.",
                    note_type="info",
                    icon="book",
                    timestamp="Today",
                    action_label="Browse Books",
                    action_url="/books",
                )
            )

    # Informational updates are treated as already seen so unread counts feel more realistic.
    for note in notifications:
        if note["type"] == "info":
            note["unread"] = False

    notification_counts = {
        "all": len(notifications),
        "unread": len([note for note in notifications if note["unread"]]),
        "alerts": len([note for note in notifications if note["type"] in ("overdue", "warning")]),
    }

    if notification_filter == "unread":
        filtered_notifications = [note for note in notifications if note["unread"]]
    elif notification_filter == "alerts":
        filtered_notifications = [note for note in notifications if note["type"] in ("overdue", "warning")]
    else:
        filtered_notifications = notifications

    stats = {
        "total_books": total_books,
        "total_users": total_users,
        "active_loans": active_loans,
        "overdue_count": overdue_count,
        "my_borrowed_books": my_borrowed_books,
        "my_due_soon": my_due_soon,
        "my_overdue": my_overdue,
        "my_returned": my_returned,
        "my_total_fine": my_total_fine,
        "total_system_fine": total_system_fine,
    }

    return render_template(
        "dashboard.html",
        user=session["user"],
        role=session.get("role", "user"),
        stats=stats,
        recent_activity=recent_activity,
        notifications=filtered_notifications,
        notification_counts=notification_counts,
        notification_filter=notification_filter,
        new_arrivals=new_arrivals,
        borrowed_now=borrowed_now,
        reading_history=reading_history,
        fine_per_day=FINE_PER_DAY,
        registered_users=registered_users,
        admin_fine_rows=admin_fine_rows,
    )


@app.route("/add_book", methods=["GET", "POST"])
def add_book():
    if not login_required() or not hydrate_session_user():
        return redirect("/login")

    if not is_admin():
        flash("Only admin can add books.", "error")
        return redirect("/books")

    if request.method == "POST":
        title = request.form["title"].strip()
        author = request.form["author"].strip()
        category = request.form["category"].strip()
        cover_url = request.form["cover_url"].strip()
        quantity = request.form["quantity"].strip()

        if not title or not author or not category or not quantity:
            return render_template("add_book.html", error="All fields except cover image are required!")

        try:
            quantity = int(quantity)
            if quantity < 0:
                return render_template("add_book.html", error="Quantity cannot be negative!")
        except ValueError:
            return render_template("add_book.html", error="Quantity must be a number!")

        cursor = get_cursor()
        cursor.execute(
            """
            INSERT INTO books (title, author, category, cover_url, quantity)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (title, author, category, cover_url, quantity),
        )
        db.commit()
        cursor.close()

        flash("Book added successfully.", "success")
        return redirect("/books")

    return render_template("add_book.html")


@app.route("/books")
def view_books():
    if not login_required() or not hydrate_session_user():
        return redirect("/login")

    search_text = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    availability = request.args.get("availability", "").strip()

    books = fetch_books(search_text=search_text, category=category, availability=availability)
    categories = fetch_categories()

    cursor = get_cursor(dictionary=True)
    cursor.execute(
        """
        SELECT book_id, borrow_id
        FROM borrow
        WHERE user_id = %s AND returned_at IS NULL
        """,
        (session["user_id"],),
    )
    borrowed_rows = cursor.fetchall()
    cursor.close()

    user_borrow_map = {row["book_id"]: row["borrow_id"] for row in borrowed_rows}

    return render_template(
        "books.html",
        books=books,
        categories=categories,
        filters={
            "q": search_text,
            "category": category,
            "availability": availability,
        },
        user_borrow_map=user_borrow_map,
        role=session.get("role", "user"),
    )


@app.route("/books/edit/<int:book_id>", methods=["GET", "POST"])
def edit_book(book_id):
    if not login_required() or not hydrate_session_user():
        return redirect("/books")

    if not is_admin():
        flash("Only admin can edit books.", "error")
        return redirect("/books")

    book = fetch_book(book_id)
    if not book:
        flash("Book not found.", "error")
        return redirect("/books")

    if request.method == "POST":
        title = request.form["title"].strip()
        author = request.form["author"].strip()
        category = request.form["category"].strip()
        cover_url = request.form["cover_url"].strip()
        quantity = request.form["quantity"].strip()

        if not title or not author or not category or not quantity:
            return render_template("edit_book.html", book=book, error="All fields except cover image are required!")

        try:
            quantity = int(quantity)
            if quantity < 0:
                return render_template("edit_book.html", book=book, error="Quantity cannot be negative!")
        except ValueError:
            return render_template("edit_book.html", book=book, error="Quantity must be a number!")

        cursor = get_cursor()
        cursor.execute(
            """
            UPDATE books
            SET title = %s, author = %s, category = %s, cover_url = %s, quantity = %s
            WHERE book_id = %s
            """,
            (title, author, category, cover_url, quantity, book_id),
        )
        db.commit()
        cursor.close()

        flash("Book updated successfully.", "success")
        return redirect("/books")

    return render_template("edit_book.html", book=book)


@app.route("/books/delete/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    if not login_required() or not hydrate_session_user():
        return redirect("/books")

    if not is_admin():
        flash("Only admin can delete books.", "error")
        return redirect("/books")

    book = fetch_book(book_id)
    if not book:
        flash("Book not found.", "error")
        return redirect("/books")

    if book["active_loans"] > 0:
        flash("You cannot delete a book that is currently borrowed.", "error")
        return redirect("/books")

    cursor = get_cursor()
    cursor.execute("DELETE FROM borrow WHERE book_id = %s", (book_id,))
    cursor.execute("DELETE FROM books WHERE book_id = %s", (book_id,))
    db.commit()
    cursor.close()

    flash("Book deleted successfully.", "success")
    return redirect("/books")


@app.route("/borrow/<int:book_id>", methods=["POST"])
def borrow_book(book_id):
    if not login_required() or not hydrate_session_user():
        return redirect("/books")

    book = fetch_book(book_id)
    if not book:
        flash("Book not found.", "error")
        return redirect("/books")

    if book["available_quantity"] <= 0:
        flash("This book is currently unavailable.", "error")
        return redirect("/books")

    cursor = get_cursor(dictionary=True)
    cursor.execute(
        """
        SELECT borrow_id
        FROM borrow
        WHERE user_id = %s AND book_id = %s AND returned_at IS NULL
        """,
        (session["user_id"], book_id),
    )
    existing_borrow = cursor.fetchone()

    if existing_borrow:
        cursor.close()
        flash("You already have this book borrowed.", "error")
        return redirect("/books")

    borrow_date = date.today()
    due_date = borrow_date + timedelta(days=14)

    cursor.execute(
        """
        INSERT INTO borrow (user_id, book_id, borrow_date, due_date)
        VALUES (%s, %s, %s, %s)
        """,
        (session["user_id"], book_id, borrow_date, due_date),
    )
    db.commit()
    cursor.close()

    flash(f"You borrowed the book successfully. Return it by {due_date}.", "success")
    return redirect("/books")


@app.route("/return/<int:borrow_id>", methods=["POST"])
def return_book(borrow_id):
    if not login_required() or not hydrate_session_user():
        return redirect("/books")

    cursor = get_cursor(dictionary=True)
    cursor.execute(
        """
        SELECT borrow_id
        FROM borrow
        WHERE borrow_id = %s AND user_id = %s AND returned_at IS NULL
        """,
        (borrow_id, session["user_id"]),
    )
    borrow_record = cursor.fetchone()

    if not borrow_record:
        cursor.close()
        flash("Borrow record not found.", "error")
        return redirect("/books")

    cursor.execute(
        "UPDATE borrow SET returned_at = %s WHERE borrow_id = %s",
        (date.today(), borrow_id),
    )
    db.commit()
    cursor.close()

    flash("Book returned successfully.", "success")
    return redirect("/dashboard")


@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("user_id", None)
    session.pop("role", None)
    flash("You have logged out successfully.", "success")
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
