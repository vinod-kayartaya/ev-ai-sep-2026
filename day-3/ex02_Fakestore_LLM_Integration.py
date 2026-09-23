import os
import sys

from myutils import line
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.tools import tool
import requests

BASE_URL = "http://fakestoreapi.com"

def init():
    global model_name
    load_dotenv()   # loads environment variables from .env file
    model_name = os.environ.get("OPENAI_MODEL_NAME")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required, but missing!")
        sys.exit(1)


@tool
def get_all_products() -> str:
    """Get all products from Fake Store API."""
    resp = requests.get(f"{BASE_URL}/products")
    resp.raise_for_status()
    return resp.text

@tool
def save_image_from_url(url: str) -> str:
    """Save the image from the URL request as a file"""
    resp = requests.get(url)
    filename = url.split("/")[-1]
    with open(filename, "wb") as file:
        file.write(resp.content)
        return f"Image saved as {filename}"


def main():
    init()

    llm = ChatOpenAI(model=model_name)
    agent = create_agent(
        model=llm,
        tools=[get_all_products, save_image_from_url],
        system_prompt="You are my shopping assistant. Respond with professionalism. Do not include emojis."
    )

    while True:
        query = input(">> ")
        if query.strip().lower() in ("quit", "exit"):
            break

        result = agent.invoke({
            "messages": [
                {
                    "role": "human",
                    "content": query
                }
            ]
        })
        print(result["messages"])



if __name__ == '__main__':
    line()
    main()
    line()
