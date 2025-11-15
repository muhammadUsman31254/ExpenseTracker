from fastmcp import FastMCP
import os
import tempfile
import aiosqlite
from datetime import datetime

# --- MCP server ---
mcp = FastMCP("Expense Tracker")

# --- Database path (writable location) ---
DB_FILE = os.path.join(tempfile.gettempdir(), "expenses.db")
print(f"Database path: {DB_FILE}")  # Optional debug

# --- Initialize DB synchronously ---
def init_db():
    import sqlite3
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("PRAGMA journal_mode=WAL")  # Allows safe concurrent writes
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
async def add_expense(amount: float, category: str, description: str = "", **kwargs) -> dict:
    """Add a new expense asynchronously"""
    date = datetime.now().strftime("%Y-%m-%d")
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
async def list_expenses(**kwargs) -> list[dict]:
    """List all expenses asynchronously"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            cur = await conn.execute("SELECT id, amount, category, description, date FROM expenses")
            rows = await cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        return [{"status": "error", "message": str(e)}]

@mcp.tool()
async def get_summary(**kwargs) -> dict:
    """Return total and category-wise expenses asynchronously"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            cur = await conn.execute("SELECT SUM(amount) FROM expenses")
            total = (await cur.fetchone())[0] or 0

            cur = await conn.execute("SELECT category, SUM(amount) FROM expenses GROUP BY category")
            breakdown_rows = await cur.fetchall()
            breakdown = {row[0]: row[1] for row in breakdown_rows}

            return {"total": total, "by_category": breakdown}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- Run server ---
if __name__ == "__main__":
    mcp.run()
