import mysql.connector

db = mysql.connector.connect(
    host="127.0.0.1",   # means your local machine
    user="root",        # MySQL username
    password="root",    # MySQL password
    database="library_db",  # your database name
    port=3307           # Docker port
)