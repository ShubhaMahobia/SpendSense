from ast import Dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
load_dotenv()
from langchain_core.messages import ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
import json
from typing import Dict
import json
from datetime import datetime
from models.transaction_schema import TransactionClassificationOutput
from prompts.prompts import Prompts





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


class UserServiceLayer:
    def __init__(self):
        self.load_contacts() #Loading contacts
        pass


    def load_contacts(self):
        with open("contacts.json", "r") as f:
            data = json.load(f)
        return {c["normalized_name"]: c for c in data.get("contacts", [])}

    def normalize(name: str) -> str:
        return name.strip().lower()

    def load_merchant_memory(self):
        try:
            with open("merchant_memory.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    def save_merchant_memory(self,memory):
        with open("merchant_memory.json", "w") as f:
            json.dump(memory, f, indent=2)

    def ask_user_for_category(self,merchant: str, from_contacts: bool = False):
        print("\n----------------------------")
        print(f"Transaction detected with: {merchant}")

        if from_contacts:
            print("We found a similar name in your contacts.")
        
        print("Please help categorize this transaction:")

        category = input("Enter category (e.g. Food & Dining / Groceries): ")
        sub_category = input("Enter sub-category: ")

        return category, sub_category


    def merchant_mapper(self,extracted_notification: Dict):

        merchant_raw = extracted_notification.get("merchant", "")
        merchant = self.normalize(merchant_raw)

        contacts = self.load_contacts()
        merchant_memory = self.load_merchant_memory()

        if merchant in merchant_memory:
            memory_entry = merchant_memory[merchant]

            extracted_notification["category"] = memory_entry["category"]
            extracted_notification["sub_category"] = memory_entry["sub_category"]

            return extracted_notification

   
        if merchant in contacts:
            category, sub_category = self.ask_user_for_category(merchant_raw, from_contacts=True)
        else:
            category, sub_category = self.ask_user_for_category(merchant_raw, from_contacts=False)

    
        extracted_notification["category"] = category
        extracted_notification["sub_category"] = sub_category

        merchant_memory[merchant] = {
            "category": category,
            "sub_category": sub_category,
            "type": "business",  # can refine later
            "source": "user_feedback",
            "usage_count": 1,
            "last_used": datetime.now().strftime("%Y-%m-%d")
        }

        self.save_merchant_memory(merchant_memory)

        return extracted_notification







    def classify_notification(self,notification_text: str, categories) -> TransactionClassificationOutput:
        model = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0)
        structured_model = model.with_structured_output(TransactionClassificationOutput)
        prompt = Prompts.get_prompt_for_classification_using_llm()
        rendered_prompt = prompt.format(
            notification_text=notification_text,
            categories=categories,
        )
        output = structured_model.invoke(rendered_prompt)
        return json.loads(output.model_dump_json())




    async def add_expense_to_db_using_llm(self,extracted_notification: Dict ):
        client = MultiServerMCPClient(SERVERS)
        tools = await client.get_tools()

        named_tools = {}
        for tool in tools:
            named_tools[tool.name] = tool


        model = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0)
        model_with_tools = model.bind_tools(tools=tools)

        

        prompt = Prompts.get_prompt_for_add_expense_to_db_using_llm()
        

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


    async def add_expense_pipeline(self):
        
        notification_message = ["Your a/c XXXXX24 debited for payee Chirag Athwani for Rs. 90.00 on 2026-01-12, ref 628944832288.If not you, report to your bank immediately-IOB."]

        with open("categories.json", "r", encoding="utf-8") as f:
            categories = json.load(f)

        for msg in notification_message:
            extracted_notif = self.classify_notification(notification_text=msg,categories=categories)
            extracted_notif1 = self.merchant_mapper(extracted_notification=extracted_notif)
            await self.llm_call(extracted_notification=extracted_notif1)









 






