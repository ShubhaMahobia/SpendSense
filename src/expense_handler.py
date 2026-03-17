from numbers import Real
import time
from typing import Literal
from mcp.server.fastmcp import FastMCP
import sqlite3
import json

from database import get_connection
from pydantic import BaseModel, Field

mcp = FastMCP('SpendSense_MCP')

categories_data = {}

with open("categories.json", "r", encoding="utf-8") as f:
    categories_data = json.load(f)


class TransactionSchema(BaseModel):
    amount: float = Field(description="Amount of transaction")
    transaction_type: str = Field(description="Type of transaction",examples=["deposit", "withdrawal", "purchase", "payment", "transfer"])
    category: str = Field(description="Type of category of the spend")
    sub_category: str = Field(description="Subtype of the category chosen")
    additional_note: str = Field(description="Any additional notes related to transaction", default= "None")
    timestamp: str = Field(description="Time and date for the transaction")
    created_at: str
    updated_at: str
    is_deleted: bool = Field(description="is transaction deleted or not", default=False)







@mcp.tool(name="Add Expense", description= "Tool for adding Expense record to the Database")
def add_expense(txn: TransactionSchema) -> str:
    """Add expense to the database"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO transactions (amount,transaction_type,category,sub_category,additional_notes,timestamp,created_at,updated_at,is_deleted) VALUES (?,?,?,?,?,?,?,?,?)
    
    
    """, (
        txn.amount,
        txn.transaction_type,
        txn.category,
        txn.sub_category,
        txn.additional_note,
        txn.timestamp,
        time.strftime("%Y-%m-%d %H:%M:%S"),
        time.strftime("%Y-%m-%d %H:%M:%S"),
        False
    ))

    conn.commit()
    return str(cursor.lastrowid)



if __name__ == "__main__":
    mcp.run(transport="stdio")



    
