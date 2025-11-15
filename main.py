from fastmcp import FastMCP
import sqlite3
import os
from datetime import datetime

# Create MCP server
mcp = FastMCP("Expense Tracker")

# Database path (absolute, relative to this file)
DB_FILE = os.path.join(os.path.dirname(__file__), "expenses.db")

# --- Initialize DB ---
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL,
                category TEXT,
                description TEXT,
                date TEXT
            )
        """)
        conn.commit()

init_db()

# --- Tools ---

@mcp.tool()
def add_expense(amount: float, category: str, description: str = "") -> str:
    """Add a new expense"""
    date = datetime.now().strftime("%Y-%m-%d")  # only date
    print(f"[ADD] {amount}, {category}, {description} on {date}")  # debug log
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO expenses (amount, category, description, date) VALUES (?, ?, ?, ?)",
            (amount, category, description, date)
        )
        conn.commit()
    return f"Added expense: {amount} in {category} ({description}) on {date}"

@mcp.tool()
def list_expenses() -> list[dict]:
    """Return all expenses"""
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id, amount, category, description, date FROM expenses")
        rows = c.fetchall()
    return [
        {"id": r[0], "amount": r[1], "category": r[2], "description": r[3], "date": r[4]}
        for r in rows
    ]

@mcp.tool()
def get_summary() -> dict:
    """Return total and category-wise expenses"""
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT SUM(amount) FROM expenses")
        total = c.fetchone()[0] or 0

        c.execute("SELECT category, SUM(amount) FROM expenses GROUP BY category")
        breakdown = {row[0]: row[1] for row in c.fetchall()}

    return {"total": total, "by_category": breakdown}

# --- Run server ---
if __name__ == "__main__":
    mcp.run()
