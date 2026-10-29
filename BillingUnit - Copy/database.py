import sqlite3


def add_column_if_missing(cursor, table, column, definition):
    columns = [
        row[1]
        for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()
    ]

    if column not in columns:
        cursor.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


def create_database():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    # Products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL
        )
    """)

    # Bills table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_no INTEGER,
            bill_date TEXT,
            total REAL,
            payment_method TEXT
        )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY,
        shop_name TEXT,
        mobile TEXT,
        address TEXT,
        bill_header TEXT
    )
""")

    # Add customer columns if they don't already exist
    add_column_if_missing(
        cursor, "bills", "customer_name", "TEXT"
    )

    add_column_if_missing(
        cursor, "bills", "customer_mobile", "TEXT"
    )

    # Bill items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bill_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER,
            product_name TEXT,
            quantity INTEGER,
            price REAL,
            total REAL
        )
    """)

    connection.commit()
    connection.close()

    print("Database created successfully!")


if __name__ == "__main__":
    create_database()