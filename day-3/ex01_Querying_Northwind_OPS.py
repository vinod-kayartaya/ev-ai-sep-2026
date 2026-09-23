import os
import sys

from myutils import line
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent


def init():
    global model_name
    load_dotenv()   # loads environment variables from .env file
    model_name = os.environ.get("OPENAI_MODEL_NAME")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required, but missing!")
        sys.exit(1)


def main():
    init()

    llm = ChatOpenAI(model=model_name)
    db = SQLDatabase.from_uri("sqlite:///database/northwind.db")
    agent = create_sql_agent(
        llm=llm,
        db=db,
        verbose=False,
    )

    template = ChatPromptTemplate.from_messages([
        ("system", "Do not execute any other SQL commands than SELECT. Give suitable errors if the user tries mutate the data."),
        ("human", "{query}")
    ])

    while True:
        query = input(">> ")
        if query.strip().lower() in ("quit", "exit"):
            break

        messages = template.invoke({"query": query}).to_messages()

        resp = agent.invoke(messages)
        print(resp["output"])
        line()



if __name__ == '__main__':
    line()
    main()
    line()
