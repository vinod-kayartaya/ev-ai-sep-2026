import os
import sys

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

def init():
    global model_name
    load_dotenv()   # loads environment variables from .env file
    model_name = os.environ.get("OPENAI_MODEL_NAME")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required, but missing!")
        sys.exit(1)


def main():
    init()

    llm = ChatOpenAI(model=model_name, max_completion_tokens=150)
    resp = llm.invoke("Tell me about Bangalore City.")

    print("-"*80)
    print(resp.content)
    print("-"*80)


if __name__ == '__main__':
    main()
