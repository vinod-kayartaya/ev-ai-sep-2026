import os
import sys

from myutils import line
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from typing import Dict


SESSION_STORE: Dict[str, InMemoryChatMessageHistory] = {}

def init():
    global model_name
    load_dotenv()   # loads environment variables from .env file
    model_name = os.environ.get("OPENAI_MODEL_NAME")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required, but missing!")
        sys.exit(1)


def get_conversational_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = InMemoryChatMessageHistory()

    return SESSION_STORE[session_id]


def main():
    init()

    llm = ChatOpenAI(model=model_name, max_completion_tokens=150)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an experienced bike mechanic who can answer any queries related "
            "to bike problems, in a professional manner. Give your answer in one sentence."),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{user_message}")
    ])

    chain = prompt | llm | StrOutputParser()

    conversational_chain = RunnableWithMessageHistory(
        chain,
        get_session_history=get_conversational_history,
        input_messages_key="user_message",
        history_messages_key="history"
    )

    while True:
        user_input = input("you > ")
        if user_input == "/q":
            break

        resp = conversational_chain.invoke(
            {"user_message": user_input},       # prompt variable inputs
            config = {"configurable": { "session_id": "vinod" }}
            )
        print(f"ai > {resp}")




if __name__ == '__main__':
    line()
    main()
    line()
