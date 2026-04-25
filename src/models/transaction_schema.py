from pydantic import BaseModel,Field
from typing import Literal


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


