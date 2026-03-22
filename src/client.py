from ast import Dict
from typing import Literal
from fastmcp.prompts import prompt
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
load_dotenv()
from langsmith.utils import P
from pydantic import BaseModel,Field
from langchain_core.messages import ToolMessage
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient


class TransactionClassificationOutput(BaseModel):
    isValid: bool = Field(description="If the message is transaction related return True otherwise False")
    amount: float = Field(description="Amount of transaction")
    merchant: str = Field(description="Who is the other party in the transaction whom we are paying to OR from whom we are recieiving money")
    transaction_type: Literal['debit','credit'] = Field(description="Type of transaction")
    category: str = Field(description="Type of category of the spend")
    sub_category: str = Field(description="Subtype of the category chosen")
    additional_note: str = Field(description="Any additional notes related to transaction", default= "None")
    timestamp: str = Field(description="Time and date for the transaction")
    confidence_score: int = Field(description="How well confident the LLM is to predict the output")


SERVERS = {
    "SpendSense_MCP" : {
    "transport" : "stdio",
    "command" : "C:/Users/mahob/anaconda3/Scripts/uv.exe",
    "args": [
        "run",
        "fastmcp",
        "run",
        "G:/Shubham/ML DL LLM/SpendSense/src/expense_handler.py"
        ]
    }
}


user_info = {
    "name" : "Shubham Mahobia",
    "curr" : "INR",
    "Bank_Account" : ["IOB", "SBI"],
    "Credit_Card_1" : "Super Money Utkarsh Bank",
    "Credit_Card_2" : "None",
    "UPI" : ["Google Pay", "Phonepe"],
    "Income" : "15000"
}



def classify_notification(notification_text: str, categories) -> TransactionClassificationOutput:
    model = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0)
    structured_model = model.with_structured_output(TransactionClassificationOutput)
    prompt = PromptTemplate(
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
    rendered_prompt = prompt.format(
        notification_text=notification_text,
        categories=categories,
    )
    output = structured_model.invoke(rendered_prompt)
    import json
    return json.loads(output.model_dump_json())


async def llm_call(extracted_notification: Dict ):
    client = MultiServerMCPClient(SERVERS)
    tools = await client.get_tools()

    named_tools = {}
    for tool in tools:
        named_tools[tool.name] = tool


    model = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0)
    model_with_tools = model.bind_tools(tools=tools)

    prompt = PromptTemplate(
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

    rendered = prompt.format(extracted_notification=extracted_notification)
    response = await model_with_tools.ainvoke(rendered)

    if not getattr(response,"tool_calls",None):
        print("LLM REPLY : ", response.content)
        return

    selected_tool = response.tool_calls[0]["name"]
    selected_tool_args = response.tool_calls[0]["args"]
    selected_tool_id = response.tool_calls[0]["id"]

    tool_result = await named_tools[selected_tool].ainvoke(selected_tool_args)

    tool_message = ToolMessage(content = tool_result,tool_name = selected_tool,tool_call_id = selected_tool_id)
    
    rendered = prompt.format(extracted_notification=extracted_notification)
    final_res = await model_with_tools.ainvoke([rendered, response, tool_message])

    return final_res


async def main_workflow():
    import json
    
    notification_message = ["Your a/c XXXXX24 debited for payee Chirag Athwani for Rs. 90.00 on 2026-03-17, ref 628944832288.If not you, report to your bank immediately-IOB."]

    with open("categories.json", "r", encoding="utf-8") as f:
        categories = json.load(f)

    for msg in notification_message:
        extracted_notif = classify_notification(notification_text=msg,categories=categories)
        await llm_call(extracted_notification=extracted_notif)






    


if __name__ == '__main__':
    asyncio.run(main_workflow())



 






