import os
import sys

from myutils import line
from time import time
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.callbacks import get_openai_callback


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

    messages = [
        ("system", "You are an authoritative human resource & employment law advisory assistent. "
            "When answering, provide direct, legally accurate and concise guidance based on standard enterprise HR policies. "
            "Do not include conversational fillers. "
            "Give your responses in bullet points (max 5)"),
        ("human", input("Enter your HR related query: "))
    ]

    start_time = time()
    chunk_count = 0
    first_token_time = None

    with get_openai_callback() as cb:
        for chunk in llm.stream(messages):
            if not first_token_time:
                first_token_time = time()

            print(chunk.content, end="", flush=True)
            chunk_count += 1

        print()
        end_time = time()
        line()
        print(f"TTFT = {first_token_time - start_time} seconds")
        print(f"Total time taken by LLM = {end_time - start_time} seconds")
        print(f"Total number of chunks received = {chunk_count}")

        print(f"Prompt (input) tokens: {cb.prompt_tokens}")
        print(f"Completion (output) tokens: {cb.completion_tokens}")
        print(f"Total tokens: {cb.total_tokens}")
        print(f"Estimated total cost (USD): {cb.total_cost:.8f}")





if __name__ == '__main__':
    line()
    main()
    line()
