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

    few_shot_template = ChatPromptTemplate.from_messages([
        ("system", "Classify the employee inquries into exactly one category: "
            "PAYROLL, LEAVES, WORKPLACE_CONDUCT, IT_EQUIPMENT, GENERAL. "
            "Provide: CATEGORY, URGENCY (LOW/MEDIUM/HIGH/CRITICAL), ASSIGNED_DEPARTMENT." ),

        # interium training
        ("human", "I didn't get my salary. I recently updated my new bank details."),
        ("ai", "CATEGORY: PAYROLL\nURGENCY: CRITICAL\nASSIGNED_DEPARTMENT: Accounting"),
        ("human", "My laptop screen goes blank frequently."),
        ("ai", "CATEGORY: IT_EQUIPMENT\nURGENCY: MEDIUM\nASSIGNED_DEPARTMENT: CCD"),
        ("human", "I saw someone smoking in the non-smoking area. What should I do?"),
        ("ai", "CATEGORY: WORKPLACE_CONDUCT\nURGENCY: MEDIUM\nASSIGNED_DEPARTMENT: Human Resources"),

        # actual query/input
        ("human", "{user_query}"),
    ])

    messages = few_shot_template.format_messages(user_query=input("Enter your query: "))
    resp = llm.invoke(messages)
    print(resp.content)


if __name__ == '__main__':
    line()
    main()
    line()
