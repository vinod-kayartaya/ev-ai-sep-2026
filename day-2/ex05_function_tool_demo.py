import os
import sys

from myutils import line
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from pprint import pprint


def init():
    global model_name
    load_dotenv()   # loads environment variables from .env file
    model_name = os.environ.get("OPENAI_MODEL_NAME")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required, but missing!")
        sys.exit(1)


# Create tools (functions) to these:
# 1. check if the given folder exists; return True or False
# 2. Create a python function to be used as langchain tool check if the folder name given violates folder policies (blacklisted: starts with / or .. or ~)
# 3. Create a python function to create a directory for the argument name. Add good docstr.

@tool
def create_directory(name):
    """
    Create a directory with the given name.

    Args:
        name (str): The name of the directory to be created.

    Raises:
        OSError: If the directory cannot be created (e.g., if it already exists).
    """
    try:
        os.makedirs(name)
        return f"Directory '{name}' created successfully."
    except OSError as e:
        return f"Error: {e}"


@tool
def is_valid_folder_name(folder_name):
    """
    Check if the provided folder name violates folder naming policies.

    The folder name is considered invalid if it:
    - Starts with a forward slash '/' (indicating an absolute path)
    - Starts with two dots '..' (indicating a parent directory)
    - Starts with a tilde '~' (commonly used for home directory shortcuts)

    Args:
        folder_name (str): The name of the folder to be checked.

    Returns:
        bool: True if the folder name is valid, False otherwise.
    """
    invalid_startings = ['/', '..', '~']
    for prefix in invalid_startings:
        if folder_name.startswith(prefix):
            return False
    return True

@tool
def check_folder_exists(folder_path):
    """
    Check if the given folder exists.

    Args:
        folder_path (str): The path of the folder to check.

    Returns:
        bool: True if the folder exists, False otherwise.
    """
    return os.path.isdir(folder_path)

@tool
def create_file_and_save_content(filename, content):
    """
    Creates a file and saves the given content in it as a plain text.
    The default location of the file created is the current working directory

    Args:
        filename: Name of the file to be created. e.g, HelloWorld.java
        content: Text content of the file created
    """
    with open(filename, "wt") as file:
        file.write(content)

    return f"File '{filename}' created successfully."


def main():
    init()
    llm = ChatOpenAI(model=model_name)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a expert polyglot programmer. "
            "Give the right code for the user's query. "
            "if the user has given a folder path, check if it exists already. "
            "if the path already exists, use the same. "
            "if the path does not exist, create a new folder path and use the same. "
            "If the user asks to save the program, but does not give filename, decide the name yourself. If the user does not mention to save the content in a file, do not create any file. "
            "while creating folders check for violations of folder creation policy. "
            "Do not give any plain text. Complete program only!"),
        ("human", "{user_input}")
    ])

    llm_with_tools = llm.bind_tools([
        create_file_and_save_content,
        create_directory,
        is_valid_folder_name,
        check_folder_exists
    ])

    tools_map = {
        "create_file_and_save_content": create_file_and_save_content,
        "create_directory": create_directory,
        "is_valid_folder_name": is_valid_folder_name,
        "check_folder_exists": check_folder_exists
    }

    chain = prompt | llm_with_tools
    # user_input = "Write and save a python script that shows the basic use of numpy"
    user_input = input("Enter your request: ")

    resp = chain.invoke({"user_input": user_input})

    if not resp.tool_calls:
        print(resp.content)


    for tool_call in resp.tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]
        tool = tools_map[name]
        result = tool.invoke(args)
        print(result)




if __name__ == '__main__':
    line()
    main()
    line()
