from langchain_core.prompts import PromptTemplate

class Prompts:
    __prompt_for_add_expense_to_db_using_llm = PromptTemplate(
            input_variables=["extracted_notification"],
            template="""
                You are a financial assistant responsible for storing transaction data using available tools.

                Your task is to:
                - Take the provided structured transaction data
                - Use the appropriate tool

                ---

                AVAILABLE TOOL:
                - Add_Expense

                ---

                INPUT TRANSACTION:
                {extracted_notification}

                ---

                INSTRUCTIONS:
                - You MUST call the "Add_Expense" tool
                - Pass the following fields:

                    Required:
                    - amount
                    - merchant
                    - transaction_type
                    - category
                    - sub_category
                    - timestamp
                    - additional_note (use "None" if missing)

                3. Do NOT:
                - Modify values unnecessarily
                - Invent new categories
                - Ask questions
                - Return JSON manually

                4. After calling the tool:
                - Respond with: "Transaction added successfully"

                ---

                IMPORTANT:
                - You are NOT responsible for extracting data
                - You are ONLY responsible for calling the correct tool
                - Always prioritize tool execution over explanation
                """
    )

    __classification_prompt_using_llm =  PromptTemplate(
            input_variables=["notification_text", "categories"],
            template="""
            You are a highly accurate financial transaction analyzer.

            Your task is to determine whether the message is a financial transaction and extract structured data.

            Rules:
            - A valid transaction must involve money movement (debit or credit)
            - Ignore OTPs, promotions, alerts, etc.

            Category Rules:
            - You MUST choose category and sub_category ONLY from the provided categories
            - Do NOT create new categories

            Schema:
            - isValid: bool
            - amount: float
            - merchant: string
            - transaction_type: debit | credit
            - category: string
            - sub_category: string
            - additional_note: string
            - timestamp: string
            - confidence_score: integer (0-100)

            INSTRUCTIONS:

                1. Extract ONLY relevant transaction information.

                2. AMOUNT:
                - Extract numeric value only
                - If missing → null

                3. MERCHANT:
                - Extract person, shop, service, or company
                - Avoid generic names unless necessary

                4. TRANSACTION TYPE:
                - debit → paid, spent, sent
                - credit → received, earned

                5. CATEGORY + SUBCATEGORY:
                - MUST strictly match from provided categories
                - Do NOT invent categories
                - Choose closest match

                6. ADDITIONAL NOTE:
                - Extract context like purpose
                - Else "None"

                7. TIMESTAMP:
                - Convert into: YYYY-MM-DD HH:MM:SS
                - If missing → null

                ---

            If NOT a transaction:
            - isValid = False

            Return ONLY valid JSON.

            Categories:
            {categories}

            Message:
            {notification_text}
            """
    )

    def __init__(self) -> None:
        pass
    
    def get_prompt_for_add_expense_to_db_using_llm(self):
        return self.__prompt_for_add_expense_to_db_using_llm


    def get_prompt_for_classification_using_llm(self):
        return self.__classification_prompt_using_llm
    