import asyncio

from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

from dotenv import load_dotenv
load_dotenv()

async def main():

    # -----------------------------------------------------
    # Connect to the local MCP server
    # -----------------------------------------------------

    client = MultiServerMCPClient(
        {
            "remote_files": {
                "url": "http://127.0.0.1:8000/mcp",
                "transport": "streamable_http",
            }
        }
    )

    # -----------------------------------------------------
    # Load the tools exposed by the MCP server
    # -----------------------------------------------------

    tools = await client.get_tools()

    print("Available MCP tools:")

    for tool in tools:
        print("-", tool.name)

    # -----------------------------------------------------
    # Create the LLM
    # -----------------------------------------------------

    llm = ChatOpenAI(
        model="gpt-4.1-mini"
    )

    # -----------------------------------------------------
    # Create the LangChain agent
    # -----------------------------------------------------

    agent = create_agent(
        llm,
        tools
    )

    # -----------------------------------------------------
    # Send a request to the agent
    # -----------------------------------------------------

    while True:
        ask = input("> ")
        if ask == "exit":
            break
        response = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": ask
                    }
                ]
            }
        )

        print("\nAgent response:")
        print(response["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())