from datetime import datetime, timedelta
from expense_handler import (
    add_expense,
    get_all_transaction,
    get_transactions,
    get_total_spending,
    get_category_subcategory_breakdown,
    TransactionSchema
)

def run_tests():
    print("\n--- Running MCP Tests ---\n")

    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # ----------------------------
    # 1. Insert Transaction
    # ----------------------------
    txn = TransactionSchema(
        amount=250,
        transaction_type="debit",
        merchant="Zomato",
        category="Food",
        sub_category="Dining",
        additional_note="Test transaction",
        timestamp=now_str,
        created_at=now_str,
        updated_at=now_str,
        is_deleted=False
    )

    print("1. Adding transaction...")
    txn_id = add_expense(txn)
    print("Inserted ID:", txn_id)

    # ----------------------------
    # 2. Duplicate Check
    # ----------------------------
    print("\n2. Testing duplicate detection...")
    duplicate = add_expense(txn)
    print("Duplicate result:", duplicate)

    # ----------------------------
    # 3. Fetch All Transactions
    # ----------------------------
    print("\n3. Fetching all transactions...")
    all_txns = get_all_transaction()
    print(f"Total transactions fetched: {len(all_txns)}")
    print("Sample:", all_txns[:1])

    # ----------------------------
    # 4. Filter Transactions
    # ----------------------------
    print("\n4. Fetching filtered transactions...")
    start_date = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    end_date = (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

    filtered = get_transactions(
        start_date=start_date,
        end_date=end_date,
        category="Food",
        merchant="Zomato",
        limit=10
    )

    print(f"Filtered results: {len(filtered)}")
    print("Sample:", filtered[:1])

    # ----------------------------
    # 5. Total Spending
    # ----------------------------
    print("\n5. Calculating total spending...")
    total = get_total_spending(
        start_date=start_date,
        end_date=end_date,
        category="Food"
    )
    print("Total spending:", total)

    # ----------------------------
    # 6. Category Breakdown
    # ----------------------------
    print("\n6. Category breakdown...")
    breakdown = get_category_subcategory_breakdown(
        start_date=start_date,
        end_date=end_date
    )
    print("Breakdown:", breakdown)

    print("\n--- All Tests Completed ---\n")


if __name__ == "__main__":
    run_tests()