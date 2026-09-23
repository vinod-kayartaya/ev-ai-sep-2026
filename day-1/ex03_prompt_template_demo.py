import os
import sys

from myutils import line
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


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

    template = ChatPromptTemplate.from_messages([
        ("system", "You are an automated Employee Operations Triage Specialist for {company_name}. "
            "Classify the user's request and summarize immediate actions required."),
        ("human", "Employee: {emp_name} (id={emp_id})\n"
            "Department: {dept_name}\n"
            "Tenure: {emp_tenure}\n"
            "Request query: {emp_query}")
    ])

    print(f"{template.input_variables = }")

    formatted_messages = template.format_messages(
        company_name="Amazon",
        emp_name="Robert Martin",
        emp_id="E-492855",
        dept_name="ACCOUNTING",
        emp_tenure="4 years 3 months",
        emp_query=input("Enter your query: ")
    )

    for m in formatted_messages:
        print(f"[{m.type.upper()}]: {m.content}")

    line()
    resp = llm.invoke(formatted_messages)
    print(resp.content)




if __name__ == '__main__':
    line()
    main()
    line()
