from pprint import pprint
import os
import sys

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import ToolMessage


def line():
    print("-" * 80)


def init():
    global model_name

    load_dotenv()

    model_name = os.environ.get("OPENAI_MODEL_NAME")

    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required, but missing!")
        sys.exit(1)


@tool
def read_file(filename: str) -> str:
    """Opens the input filename for reading, assuming it is a text file.
    Returns the content of the file read.

    Arguments:
        filename - name of the input file

    Returns:
        The content of the file
    """
    with open(filename, "rt") as file:
        return file.read()


@tool
def write_to_file(filename: str, content: str) -> str:
    """Writes or saves the given content to the file.
    Overwrites the file if it already exists.

    Arguments:
        filename - name of the file to write
        content - text content to be written to the file

    Returns:
        Status of completion
    """
    with open(filename, "wt") as file:
        file.write(content)

    return f"The file '{filename}' was written successfully"


def main():

    init()

    tools = [
        read_file,
        write_to_file
    ]

    tools_map = {
        "read_file": read_file,
        "write_to_file": write_to_file
    }

    llm = ChatOpenAI(
        model=model_name,
    ).bind_tools(tools)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are an expert software developer.

Answer the user's request professionally.

You have access to tools for reading and writing files.

Use read_file when the user asks you to read a file.

Use write_to_file when the user asks you to create or modify a file.

If the user's request requires multiple file operations,
perform them in the required sequence.
"""
        ),
        ("human", "{user_prompt}")
    ])

    user_prompt = input("Hi, what can I do for you? ")

    # Create the initial conversation
    messages = prompt.invoke({
        "user_prompt": user_prompt
    }).to_messages()

    while True:

        # ---------------------------------------------------------
        # 1. Send conversation to LLM
        # ---------------------------------------------------------
        resp = llm.invoke(messages)

        # ---------------------------------------------------------
        # 2. No tool calls -> final response
        # ---------------------------------------------------------
        if not resp.tool_calls:
            print(resp.content)
            break

        # ---------------------------------------------------------
        # 3. Add the AIMessage containing the tool calls
        # ---------------------------------------------------------
        messages.append(resp)

        print("\nTool calls:")
        pprint(resp.tool_calls)

        # ---------------------------------------------------------
        # 4. Execute every requested tool
        # ---------------------------------------------------------
        for tc in resp.tool_calls:

            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id = tc["id"]

            print(f"\nExecuting tool: {tool_name}")
            print(f"Arguments: {tool_args}")

            tool_resp = tools_map[tool_name].invoke(tool_args)

            print(f"Tool response: {tool_resp}")

            # -----------------------------------------------------
            # 5. Add the tool result to the conversation
            # -----------------------------------------------------
            messages.append(
                ToolMessage(
                    content=tool_resp,
                    tool_call_id=tool_id
                )
            )


if __name__ == '__main__':
    line()
    main()
    line()