from numbers import Real
import time
from typing import Literal, Optional
from fastmcp import FastMCP
import sqlite3
import hashlib
import json

from database import get_connection
from pydantic import BaseModel, Field

mcp = FastMCP('SpendSense_MCP')

categories_data = {}

with open("categories.json", "r", encoding="utf-8") as f:
    categories_data = json.load(f)




class TransactionSchema(BaseModel):
    amount: float = Field(description="Amount of transaction")
    transaction_type: str = Field(description="Type of transaction",examples=["debit","credit"])
    merchant: str = Field(description="Who is the other party in the transaction whom we are paying to OR from whom we are recieiving money")
    category: str = Field(description="Type of category of the spend")
    sub_category: str = Field(description="Subtype of the category chosen")
    additional_note: str = Field(description="Any additional notes related to transaction", default= "None")
    timestamp: str = Field(description="Time and date for the transaction")
    created_at: str
    updated_at: str
    is_deleted: bool = Field(description="is transaction deleted or not", default=False)







@mcp.tool(name="Add_Expense", description= "Tool for adding Expense record to the Database")
def add_expense(txn: TransactionSchema) -> str:
    """Add expense to the database"""
    conn = get_connection()
    cursor = conn.cursor()
    def hash_string(input_string: str) -> str:
        # Convert string to bytes
        encoded = input_string.encode('utf-8')
        
        # Create hash object (SHA-256)
        hash_obj = hashlib.sha256(encoded)
        
        # Get hexadecimal representation
        return hash_obj.hexdigest()    

    # Checking Duplicate Entry - 
    combined_string = f"{txn.amount}{txn.transaction_type}{txn.timestamp}{txn.category}{txn.merchant}"
    hashed_string = hash_string(combined_string)

    cursor.execute(
        "SELECT 1 FROM hashed_tranxn WHERE hashed_string = ? LIMIT 1",
        (hashed_string,)
    )
    exists = cursor.fetchone()

    if exists:
        return "Duplicate Transaction"
    else:
        cursor.execute("""INSERT INTO hashed_tranxn(hashed_string) VALUES (?)""",(hashed_string,))
        cursor.execute("""
                INSERT INTO transactions (amount,transaction_type,category,merchant,sub_category,additional_notes,timestamp,created_at,updated_at,is_deleted) VALUES (?,?,?,?,?,?,?,?,?,?)
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


    conn.commit()
    return str(cursor.lastrowid)


@mcp.tool(name = "get_transaction" , description= "Fetches all the transaction from the DB")
def get_all_transaction():
    conn = get_connection()
    cursor= conn.cursor()

    cursor.execute("""
        SELECT * FROM transactions ORDER BY timestamp DESC
    """)

    rows = cursor.fetchall()

    return [dict(row) for row in rows]


@mcp.tool(name='get_transaction_detail',description="Get specific transaction from the DB")
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
        query += " AND timestamp >= ?"
        params.append(start_date)

    if end_date:
        query += " AND timestamp <= ?"
        params.append(end_date)

    if category:
        query += " AND category = ?"
        params.append(category)

    if sub_category:
        query += " AND sub_category LIKE ?"
        params.append(f"%{sub_category}%")

    if merchant:
        query += " AND merchant LIKE ?"
        params.append(f"%{merchant}%")

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    return [dict(row) for row in rows]

@mcp.tool(name = "get_total_spending", description="Total spending in specified range")
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
    WHERE (transaction_type = 'debit')
    AND timestamp >= ?
    AND timestamp <= ?
    """

    params = [start_date, end_date]

    if category:
        query += " AND category = ?"
        params.append(category)

    cursor.execute(query, params)
    result = cursor.fetchone()

    return {
        "total_amount": result["total"] or 0
    }

@mcp.tool(name = "get_category_subcategory_breakdown",description="Get data based on cateogy and sub category wise")
def get_category_subcategory_breakdown(start_date: Optional[str] = None, end_date: Optional[str] = None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT category, subcategory, SUM(amount) as total
    FROM transactions
    WHERE transaction_type = 'debit'
    """
    params = []

    if start_date:
        query += " AND timestamp >= ?"
        params.append(start_date)

    if end_date:
        query += " AND timestamp <= ?"
        params.append(end_date)

    query += " GROUP BY category, subcategory"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    # Transform into nested dict
    result = {}

    for row in rows:
        category = row["category"] or "Miscellaneous"
        subcategory = row["subcategory"] or "Other"
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



    
