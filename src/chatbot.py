from langgraph.graph import START, END, StateGraph, add_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from dotenv import load_dotenv
from typing import Literal, Optional, TypedDict, Annotated
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.prompts import PromptTemplate
import operator
import json

from pydantic import BaseModel, Field
load_dotenv()
import asyncio


async def main():

    model = ChatGoogleGenerativeAI(model = 'gemini-3.1-flash-lite-preview')

    class ChatbotState(TypedDict):
        messages: Annotated[list[BaseMessage],add_messages]
        extracted_data: Optional[dict]
        is_small_talk: Optional[bool]

    


    graph = StateGraph(ChatbotState)

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

    class QueryExtractionOutput(BaseModel):
        amount: float = Field(description="Amount of transaction")
        merchant: str = Field(description="Who is the other party in the transaction whom we are paying to OR from whom we are recieiving money")
        transaction_type: Literal['debit','credit'] = Field(description="Type of transaction")
        category: str = Field(description="Type of category of the spend")
        sub_category: str = Field(description="Subtype of the category chosen")
        additional_note: str = Field(description="Any additional notes related to transaction", default= "None")
        timestamp: str = Field(description="Time and date for the transaction")
        
    async def chat_function(state: ChatbotState):
        extracted = state.get("extracted_data")
        client = MultiServerMCPClient(SERVERS)
        tools = await client.get_tools()

        # Map tools
        named_tools = {tool.name: tool for tool in tools}
        tool_names = list(named_tools.keys())

        # Bind model with tools
        model_with_tools = model.bind_tools(tools=tools)

        # Prepare tool description (important for prompt clarity)
        tools_description = "\n".join(
            [f"{tool.name}: {tool.description}" for tool in tools]
        )

        # Prompt
        chatbot_prompt1 = PromptTemplate(
            input_variables=["user_query", "tools", "tool_names"],
            template="""
            You are an intelligent and reliable assistant.

            Your goal is to help the user by understanding their query and deciding whether to:
            1. Answer directly, OR
            2. Use available tools to perform an action

            ---

            AVAILABLE TOOLS:
            {tools}

            Tool Names:
            {tool_names}

            ---

            INSTRUCTIONS:

            1. Carefully analyze the user query:
            - If the query requires real-world actions, calculations, database access, or external data → USE a tool
            - If the query is informational or conversational → respond directly

            2. When using a tool:
            - Select the most appropriate tool
            - Pass correct and complete arguments
            - Do NOT guess missing values unless very obvious
            - Do NOT call multiple tools unless necessary

            3. Tool Usage Rules:
            - Always prioritize tool execution over explanation when needed
            - Do NOT explain what you are doing before calling the tool
            - After tool execution, return a clear and final answer to the user

            4. If no tool is needed:
            - Provide a helpful, concise, and accurate response

            5. Never:
            - Hallucinate tool outputs
            - Invent tools or parameters
            - Ask unnecessary follow-up questions

            ---

            USER QUERY:
            {user_query}

            ---
            Your response:
            """
        )
        chatbot_prompt2 = PromptTemplate(
            input_variables=["user_query", "tools", "tool_names", "extracted_data"],
            template="""
                You are an intelligent assistant with access to structured transaction data.

                Your job is to respond to the user and use tools when necessary.

                ---

                AVAILABLE TOOLS:
                {tools}

                Tool Names:
                {tool_names}

                ---

                USER QUERY:
                {user_query}

                ---

                EXTRACTED TRANSACTION DATA:
                {extracted_data}

                ---

                INSTRUCTIONS:

                1. Use the extracted transaction data as the primary source of truth.
                - Prefer extracted_data over interpreting the user query
                - Do NOT re-extract or reinterpret information already provided

                2. When calling tools:
                - Use fields from extracted_data directly as arguments
                - Ensure arguments match tool requirements
                - If some fields are missing, use the user query only to fill gaps carefully

                3. Maintain consistency:
                - Do not change values from extracted_data unless clearly incorrect
                - Do not invent or hallucinate missing fields

                4. If a tool is required:
                - Call the most appropriate tool
                - Pass clean and structured arguments

                5. If no tool is required:
                - Respond clearly and helpfully to the user

                ---

                RULES:

                - Do NOT explain tool usage before calling it
                - Do NOT hallucinate tool outputs
                - Do NOT ignore extracted_data when it is available
                - Keep responses concise and accurate

                ---

                Your response:
                """
        )

        # Get user query from state
        user_query = state["messages"][-1].content

        if extracted:
            rendered = chatbot_prompt2.format(
                user_query=user_query,
                tools=tools_description,
                tool_names=", ".join(tool_names),
                extracted_data = extracted
            )
        else:
            rendered = chatbot_prompt1.format(
                user_query=user_query,
                tools=tools_description,
                tool_names=", ".join(tool_names),
            )

        # First LLM call
        response = await model_with_tools.ainvoke(rendered)

        # If no tool call → return direct response
        if not getattr(response, "tool_calls", None):
            return {"messages": [AIMessage(content=response.content)]}

        # Handle tool call
        tool_call = response.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_call_id = tool_call["id"]

        # Execute tool
        tool_result = await named_tools[tool_name].ainvoke(tool_args)
        print(f"[DEBUG] Tool called: {tool_name}")
        # Create tool message
        tool_message = ToolMessage(
            content=str(tool_result),
            tool_name=tool_name,
            tool_call_id=tool_call_id,
        )

        # Second LLM call (final response)
        final_response = await model_with_tools.ainvoke([
                HumanMessage(content=rendered),
                response,
                tool_message,
                HumanMessage(content="""
            Use the tool result above to answer the user's question.

            - If the user asked for total amount → SUM the amounts
            - If filtering is needed → apply it
            - Return a clear final answer

            Do NOT call any tool again.
            """)
            ])

        return {"messages": [final_response]}

    async def query_extractor(state: ChatbotState):
        messages = state["messages"]
        user_input = messages[-1].content if messages else ""

        with open("categories.json", "r", encoding="utf-8") as f:
            categories = json.load(f)

        
        prompt = PromptTemplate(
            input_variables=["user_input", "categories"],
            template="""
            You are a financial transaction extraction engine.

            Your job is to extract structured data from user input.

            ---

            USER INPUT:
            {user_input}

            ---

            VALID CATEGORIES (STRICT):
            {categories}

            ---

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

            OUTPUT FORMAT (STRICT JSON ONLY):

            {{
                "amount": float | null,
                "merchant": string | null,
                "transaction_type": "debit" | "credit" | null,
                "category": string | null,
                "sub_category": string | null,
                "additional_note": string,
                "timestamp": string | null
            }}

            ---

            DO NOT:
            - Add explanation
            - Add extra fields
            - Hallucinate categories
            - Return invalid JSON

            """
            )

        structured_model = model.with_structured_output(QueryExtractionOutput)

        formatted_prompt = prompt.format(
            user_input=user_input,
            categories=json.dumps(categories, indent=2)
        )

        output = structured_model.invoke(formatted_prompt)

        return {
        "extracted_data": output.model_dump()
        }
        
    async def handle_small_talk(state: ChatbotState):
        messages = state["messages"]
        user_input = messages[-1].content if messages else ""

        prompt = f"""
                Is this message small talk?

                Return ONLY: true or false

                Message:
                {user_input}
                """

        response = await model.ainvoke(prompt)
        result = response.content[0]['text'].lower().strip()

        is_small_talk = result == "true"

        # ✅ If small talk → respond immediately
        if is_small_talk:
            reply = await model.ainvoke(f"""
                        You are a friendly assistant.

                        Respond naturally to this small talk:

                        {user_input}
                        """)

            return {
                "messages": [AIMessage(content=reply.content)],
                "is_small_talk": True
            }

        # ✅ If NOT small talk → just pass state forward
        return {
            "is_small_talk": False
        }

    def small_talk_router(state: ChatbotState):
        if state.get("is_small_talk"):
            return "end"   
        return "query_extraction"

    graph.add_node('query_extraction', query_extractor)
    graph.add_node('chat_node',chat_function)
    graph.add_node("small_talk", handle_small_talk)



    graph.add_edge(START, 'small_talk')
    graph.add_conditional_edges("small_talk",small_talk_router,{"query_extraction": "query_extraction","end": END})
    graph.add_edge('query_extraction','chat_node')
    graph.add_edge('chat_node',END)

    chatbot = graph.compile()

    thread_id = '1'

    while True:
        user_message = input("Type here : ")

        print('User : ', user_message)

        if user_message.strip().lower() in ['exit', 'quit', 'bye']:
            break

        config = {'configurable': {'thread_id': thread_id}}
        response = await chatbot.ainvoke({'messages': [HumanMessage(content=user_message)]}, config=config)

        last = response["messages"][-1]
        print("AI : ", getattr(last, "text", str(last.content)))
      


if __name__ == "__main__":
    asyncio.run(main())