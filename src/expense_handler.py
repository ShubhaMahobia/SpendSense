import time
from typing import Optional
from fastmcp import FastMCP
import hashlib
import json

from database import get_connection
from pydantic import BaseModel, Field

mcp = FastMCP('SpendSense_MCP')

categories_data = {}

with open("categories.json", "r", encoding="utf-8") as f:
    categories_data = json.load(f)


class TransactionSchema(BaseModel):
    amount: float
    transaction_type: str
    merchant: str
    category: str
    sub_category: str
    additional_note: str = "None"
    timestamp: str
    created_at: str
    updated_at: str
    is_deleted: bool = False


def hash_string(input_string: str) -> str:
    return hashlib.sha256(input_string.encode('utf-8')).hexdigest()


@mcp.tool(name="Add_Expense", description="Tool for adding Expense record to the Database")
def add_expense(txn: TransactionSchema) -> str:
    conn = get_connection()
    cursor = conn.cursor()

    combined_string = f"{txn.amount}{txn.transaction_type}{txn.timestamp}{txn.category}{txn.merchant}"
    hashed_string = hash_string(combined_string)

    cursor.execute(
        "SELECT 1 FROM hashed_tranxn WHERE hashed_string = %s LIMIT 1",
        (hashed_string,)
    )
    exists = cursor.fetchone()

    if exists:
        cursor.close()
        conn.close()
        return "Duplicate Transaction"

    # insert hash
    cursor.execute(
        "INSERT INTO hashed_tranxn(hashed_string) VALUES (%s)",
        (hashed_string,)
    )

  
    cursor.execute("""
        INSERT INTO transactions (
            amount, transaction_type, category, merchant,
            sub_category, additional_notes, timestamp,
            created_at, updated_at, is_deleted
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (
        txn.amount,
        txn.transaction_type,
        txn.category,
        txn.merchant,
        txn.sub_category,
        txn.additional_note,
        txn.timestamp,
        time.strftime("%Y-%m-%d %H:%M:%S"),
        time.strftime("%Y-%m-%d %H:%M:%S"),
        False
    ))

    txn_id = cursor.fetchone()["id"]

    conn.commit()
    cursor.close()
    conn.close()

    return str(txn_id)


@mcp.tool(name="get_transaction", description="Fetches all the transaction from the DB")
def get_all_transaction():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM transactions ORDER BY timestamp DESC
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [dict(row) for row in rows]


@mcp.tool(name='get_transaction_detail', description="Get specific transaction from the DB")
def get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    sub_category: Optional[str] = None,
    merchant: Optional[str] = None,
    limit: int = 100
):
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM transactions WHERE 1=1"
    params = []

    if start_date:
        query += " AND timestamp >= %s"
        params.append(start_date)

    if end_date:
        query += " AND timestamp <= %s"
        params.append(end_date)

    if category:
        query += " AND category = %s"
        params.append(category)

    if sub_category:
        query += " AND sub_category ILIKE %s"
        params.append(f"%{sub_category}%")

    if merchant:
        query += " AND merchant ILIKE %s"
        params.append(f"%{merchant}%")

    query += " ORDER BY timestamp DESC LIMIT %s"
    params.append(limit)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [dict(row) for row in rows]


@mcp.tool(name="get_total_spending", description="Total spending in specified range")
def get_total_spending(
    start_date: str,
    end_date: str,
    category: Optional[str] = None
):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT SUM(amount) as total
    FROM transactions
    WHERE transaction_type = 'debit'
    AND timestamp >= %s
    AND timestamp <= %s
    """

    params = [start_date, end_date]

    if category:
        query += " AND category = %s"
        params.append(category)

    cursor.execute(query, tuple(params))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return {
        "total_amount": result["total"] or 0
    }


@mcp.tool(name="get_category_subcategory_breakdown", description="Get data based on category and sub category wise")
def get_category_subcategory_breakdown(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT category, sub_category, SUM(amount) as total
    FROM transactions
    WHERE transaction_type = 'debit'
    """
    params = []

    if start_date:
        query += " AND timestamp >= %s"
        params.append(start_date)

    if end_date:
        query += " AND timestamp <= %s"
        params.append(end_date)

    query += " GROUP BY category, sub_category"

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    result = {}

    for row in rows:
        category = row["category"] or "Miscellaneous"
        subcategory = row["sub_category"] or "Other"
        amount = row["total"] or 0

        if category not in result:
            result[category] = {
                "total": 0,
                "subcategories": {}
            }

        result[category]["subcategories"][subcategory] = amount
        result[category]["total"] += amount

    return result


if __name__ == "__main__":
    mcp.run()