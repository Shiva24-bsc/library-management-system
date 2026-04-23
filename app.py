from datetime import date, timedelta

from flask import Flask, flash, redirect, render_template, request, session

from config import db

app = Flask(__name__)
app.secret_key = "secret123"


def get_cursor(dictionary=False):
    db.ping(reconnect=True, attempts=3, delay=2)
    return db.cursor(dictionary=dictionary)


def ensure_schema():
    cursor = get_cursor()

    # created_at helps us show new arrivals on the dashboard.
    cursor.execute("SHOW COLUMNS FROM books LIKE 'created_at'")
    if not cursor.fetchone():
        cursor.execute(
            """
            ALTER TABLE books
            ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """
        )

    # cover_url lets us show book cover images in the interface.
    cursor.execute("SHOW COLUMNS FROM books LIKE 'cover_url'")
    if not cursor.fetchone():
        cursor.execute(
            """
            ALTER TABLE books
            ADD COLUMN cover_url VARCHAR(500) NULL AFTER category
            """
        )

    # due_date is needed to show realistic return deadlines.
    cursor.execute("SHOW COLUMNS FROM borrow LIKE 'due_date'")
    if not cursor.fetchone():
        cursor.execute(
            """
            ALTER TABLE borrow
            ADD COLUMN due_date DATE NULL AFTER borrow_date
            """
        )

    # returned_at helps us separate active borrowing from completed returns.
    cursor.execute("SHOW COLUMNS FROM borrow LIKE 'returned_at'")
    if not cursor.fetchone():
        cursor.execute(
            """
            ALTER TABLE borrow
            ADD COLUMN returned_at DATE NULL AFTER due_date
            """
        )

    cursor.execute(
        """
        UPDATE borrow
        SET due_date = DATE_ADD(borrow_date, INTERVAL 14 DAY)
        WHERE due_date IS NULL AND borrow_date IS NOT NULL
        """
    )

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
    return "user" in session


def hydrate_session_user():
    if "user" not in session:
        return False

    if "user_id" in session and "role" in session:
        return True

    cursor = get_cursor(dictionary=True)
    cursor.execute(
        "SELECT user_id, role FROM users WHERE name = %s LIMIT 1",
        (session["user"],),
    )
    user = cursor.fetchone()
    cursor.close()

    if not user:
        session.clear()
        return False

    session["user_id"] = user["user_id"]
    session["role"] = user.get("role", "user")
    return True


def is_admin():
    return session.get("role") == "admin"


def days_ago_label(value):
    if not value:
        return ""
    diff = (date.today() - value).days
    if diff <= 0:
        return "today"
    if diff == 1:
        return "1 day ago"
    return f"{diff} days ago"


def due_status_label(due_date):
    if not due_date:
        return ("Unknown", "info")

    diff = (due_date - date.today()).days

    if diff < 0:
        return (f"Overdue by {abs(diff)} day(s)", "overdue")
    if diff == 0:
        return ("Due today", "warning")
    if diff == 1:
        return ("Due tomorrow", "warning")
    return (f"Due in {diff} days", "borrowed")


def fetch_book(book_id):
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

    if category:
        query += " AND b.category = %s"
        params.append(category)

    if availability == "available":
        query += " AND GREATEST(b.quantity - COALESCE(active.active_loans, 0), 0) > 0"
    elif availability == "borrowed":
        query += " AND GREATEST(b.quantity - COALESCE(active.active_loans, 0), 0) = 0"

    query += " ORDER BY b.title ASC"

    cursor.execute(query, tuple(params))
    books = cursor.fetchall()
    cursor.close()

    # Simple status labels make availability easier to understand at a glance.
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
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"].strip()

        if not name or not email or not password:
            return render_template("register.html", error="All fields are required!")

        cursor = get_cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        existing_user = cursor.fetchone()

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
        email = request.form["email"].strip()
        password = request.form["password"].strip()

        if not email or not password:
            return render_template("login.html", error="Please enter both email and password!")

        cursor = get_cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if not user:
            return render_template("login.html", error="User not found!")

        if user["password"] != password:
            return render_template("login.html", error="Wrong password!")

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

    cursor = get_cursor(dictionary=True)

    # Global stats are still useful for admins.
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

    # User-focused counts make the dashboard feel personal instead of generic.
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

    # Current borrowed books for direct user action on the dashboard.
    cursor.execute(
        """
        SELECT
            b.borrow_id,
            bk.title,
            bk.author,
            bk.category,
            bk.cover_url,
            b.borrow_date,
            b.due_date
        FROM borrow b
        JOIN books bk ON bk.book_id = b.book_id
        WHERE b.user_id = %s AND b.returned_at IS NULL
        ORDER BY b.due_date ASC
        LIMIT 5
        """,
        (session["user_id"],),
    )
    borrowed_now = cursor.fetchall()

    # Reading history helps the dashboard feel real and useful.
    cursor.execute(
        """
        SELECT
            b.borrow_id,
            bk.title,
            bk.author,
            bk.cover_url,
            b.borrow_date,
            b.returned_at
        FROM borrow b
        JOIN books bk ON bk.book_id = b.book_id
        WHERE b.user_id = %s AND b.returned_at IS NOT NULL
        ORDER BY b.returned_at DESC
        LIMIT 5
        """,
        (session["user_id"],),
    )
    reading_history = cursor.fetchall()

    # Recent activity is still useful for both admin and user.
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

    cursor.execute(
        """
        SELECT title, author, category, cover_url, created_at
        FROM books
        ORDER BY created_at DESC
        LIMIT 4
        """
    )
    new_arrivals = cursor.fetchall()

    cursor.close()

    for item in borrowed_now:
        item["borrowed_label"] = days_ago_label(item["borrow_date"])
        status_text, status_class = due_status_label(item["due_date"])
        item["due_status_text"] = status_text
        item["due_status_class"] = status_class

    for item in reading_history:
        item["borrowed_label"] = days_ago_label(item["borrow_date"])

    notifications = []

    if my_overdue > 0:
        notifications.append(
            {
                "title": f"You have {my_overdue} overdue book(s)",
                "detail": "Please return them as soon as possible to keep your record up to date.",
                "type": "overdue",
            }
        )

    if my_due_soon > 0:
        notifications.append(
            {
                "title": f"{my_due_soon} book(s) due soon",
                "detail": "Check the due dates below and return them on time.",
                "type": "warning",
            }
        )

    for item in new_arrivals[:2]:
        notifications.append(
            {
                "title": f"New book added: {item['title']}",
                "detail": f"Recently added in {item['category']} by {item['author']}.",
                "type": "info",
            }
        )

    # Keep both system-wide and personal stats available.
    stats = {
        "total_books": total_books,
        "total_users": total_users,
        "active_loans": active_loans,
        "overdue_count": overdue_count,
        "my_borrowed_books": my_borrowed_books,
        "my_due_soon": my_due_soon,
        "my_overdue": my_overdue,
        "my_returned": my_returned,
    }

    return render_template(
        "dashboard.html",
        user=session["user"],
        role=session.get("role", "user"),
        stats=stats,
        recent_activity=recent_activity,
        notifications=notifications,
        new_arrivals=new_arrivals,
        borrowed_now=borrowed_now,
        reading_history=reading_history,
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
        return redirect("/login")

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
        return redirect("/login")

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
        return redirect("/login")

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
        return redirect("/login")

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
