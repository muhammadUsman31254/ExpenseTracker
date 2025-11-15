from fastmcp import FastMCP
import os
import tempfile
import aiosqlite
from datetime import datetime

# --- MCP server ---
mcp = FastMCP("Expense Tracker")

# --- Database path (writable location) ---
DB_FILE = os.path.join(tempfile.gettempdir(), "expenses.db")
print(f"Database path: {DB_FILE}")

# --- Initialize DB synchronously ---
def init_db():
    import sqlite3
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
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
async def add_expense(amount: float, category: str, description: str = "", date: str = None) -> dict:
    """Add a new expense asynchronously, optional date (YYYY-MM-DD)"""
    date = date or datetime.now().strftime("%Y-%m-%d")
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            cur = await conn.execute(
                "INSERT INTO expenses (amount, category, description, date) VALUES (?, ?, ?, ?)",
                (amount, category, description, date)
            )
            await conn.commit()
            return {"status": "success", "id": cur.lastrowid, "message": f"Added {amount} in {category} on {date}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def list_expenses(start_date: str = None, end_date: str = None, category: str = None) -> list[dict]:
    """
    List expenses optionally filtered by date range and category.
    Dates must be in YYYY-MM-DD format.
    """
    start_date = start_date or "1900-01-01"
    end_date = end_date or "2100-12-31"

    query = "SELECT id, amount, category, description, date FROM expenses WHERE date BETWEEN ? AND ?"
    params = [start_date, end_date]

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY date DESC, id DESC"

    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            cur = await conn.execute(query, params)
            rows = await cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        return [{"status": "error", "message": str(e)}]

@mcp.tool()
async def get_summary(start_date: str = None, end_date: str = None, category: str = None) -> dict:
    """
    Summarize total and category-wise expenses optionally filtered by date range and category.
    """
    start_date = start_date or "1900-01-01"
    end_date = end_date or "2100-12-31"

    total_query = "SELECT SUM(amount) FROM expenses WHERE date BETWEEN ? AND ?"
    breakdown_query = "SELECT category, SUM(amount) FROM expenses WHERE date BETWEEN ? AND ?"
    params = [start_date, end_date]

    if category:
        total_query += " AND category = ?"
        breakdown_query += " AND category = ?"
        params.append(category)

    breakdown_query += " GROUP BY category ORDER BY SUM(amount) DESC"

    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            cur = await conn.execute(total_query, params)
            total = (await cur.fetchone())[0] or 0

            cur = await conn.execute(breakdown_query, params)
            rows = await cur.fetchall()
            breakdown = {row[0]: row[1] for row in rows}

            return {"total": total, "by_category": breakdown}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- Run server ---
if __name__ == "__main__":
    mcp.run()
