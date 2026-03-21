from langgraph.graph import START, END, StateGraph, add_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from dotenv import load_dotenv
from typing import TypedDict, Annotated
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.prompts import PromptTemplate
import operator
load_dotenv()
import asyncio


async def main():

    model = ChatGoogleGenerativeAI(model = 'gemini-3.1-flash-lite-preview')

    class ChatbotState(TypedDict):
        messages: Annotated[list[BaseMessage],add_messages]


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
        
    async def chat_function(state: ChatbotState):
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
        chatbot_prompt = PromptTemplate(
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

        # Get user query from state
        user_query = state["messages"][-1].content

        rendered = chatbot_prompt.format(
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
            tool_message
        ])

        return {"messages": [final_response]}


    graph.add_node('chatnode',chat_function)

    graph.add_edge(START, 'chatnode')
    graph.add_edge('chatnode', END)

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