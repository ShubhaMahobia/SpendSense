from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel,Field


class TransactionClassificationOutput(BaseModel):
    isValid: bool = Field(description="If the message is transaction related return True otherwise False")
    confidence_score: int = Field(description="How well confident the LLM is to predict the output")
    amount: float = Field(description="Amount of the transaction")
    transaction_type: str = Field(
        description="Type of transaction",
        examples=["deposit", "withdrawal", "purchase", "payment", "transfer"]
    )
    merchant: str = Field(description="Merchant of the Payment, Who is the second party of payment",default="Others")
    timestamp: str = Field(description="Time and date of transaction")


user_info = {
    "name" : "Shubham Mahobia",
    "curr" : "INR",
    "Bank_Account" : ["IOB", "SBI"],
    "Credit_Card_1" : "Super Money Utkarsh Bank",
    "Credit_Card_2" : "None",
    "UPI" : ["Google Pay", "Phonepe"],
    "Income" : "15000"
}



def classify_notification(notification_text: str):
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    structured_model = model.with_structured_output(TransactionClassificationOutput)
    prompt = (
        "You are a highly accurate context analyzer, specialized in identifying financial transactions. "
        "Analyze the provided message and determine if it relates specifically to a money credit or debit "
        "(such as deposit, withdrawal, purchase, payment, transfer, fund receipt, or any indication of an "
        "account balance change). Only classify the message as a transaction if it clearly indicates money moving "
        "in or out of an account, wallet, or card. Do not consider non-monetary transactions (like account updates, "
        "password changes, or notification of non-financial activity) as valid transactions.\n\n"
        "If the message is a financial transaction, extract the following details as per the schema below:\n"
        "- isValid: Return True if the message is transaction-related, False otherwise.\n"
        "- confidence_score: Integer between 0-100 estimating your confidence in classification and extraction.\n"
        "- amount: The monetary value involved (float), or 0 if not found.\n"
        "- transaction_type: One of [deposit, withdrawal, purchase, payment, transfer] or a close match.\n"
        "- merchant: Extract the name or identifier of the second party (merchant/beneficiary) involved, or 'Unknown'.\n"
        "- timestamp: Extract the precise time/date if present, else 'Unknown'.\n\n"
        "If the message is NOT related to financial transactions, isValid should be False and other fields populated as accurately as possible or 'Unknown'.\n\n"
        f"Message:\n{notification_text}"
    )
    output = structured_model.invoke(prompt)
    return output





 






