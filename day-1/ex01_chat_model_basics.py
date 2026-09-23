import os
import sys
from myutils import line

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


def init():
    global model_name
    load_dotenv()   # loads environment variables from .env file
    model_name = os.environ.get("OPENAI_MODEL_NAME")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required, but missing!")
        sys.exit(1)


def main():
    init()

    llm = ChatOpenAI(model=model_name, max_completion_tokens=150, temperature=1.0)

    system_prompt = (
        "You are an authoritative human resource & employment law advisory assistent. "
        "When answering, provide direct, legally accurate and concise guidance based on standard enterprise HR policies. "
        "Do not include conversational fillers. "
        "Give your responses in bullet points (max 5)"
    )
    user_prompt = input("Enter your HR related query: ")

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    resp = llm.invoke(messages)
    print(resp.content)


if __name__ == '__main__':
    line()
    main()
    line()
