from fastmcp import FastMCP
import sqlite3

mcp = FastMCP('SpendSense_MCP')

mcp.tool(name="Add Expense", description= "Tool for adding Expense record to the Database")
def add_expense():
    """Add expense to the database"""
    
