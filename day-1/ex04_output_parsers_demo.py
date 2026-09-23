import os
import sys

from myutils import line
from dotenv import load_dotenv

from pprint import pprint
from typing import Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser, PydanticOutputParser


def init():
    global model_name
    load_dotenv()   # loads environment variables from .env file
    model_name = os.environ.get("OPENAI_MODEL_NAME")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required, but missing!")
        sys.exit(1)


class LeaveRequest(BaseModel):
    """Structured information about a leave request by an employee"""
    employee_id: str|None = Field(description="Internal employee id (e.g, E9482747)")
    employee_name: str = Field(description="Full name of the employee")
    employee_phone: str = Field(description="Phone number of the employee")
    # leave_type: Literal["PERSONAL_TIME_OFF", "SICK_LEAVE", "PARENTAL_LEAVE", "UNPAID_SABBATICAL"]|None = Field(description="Types of leaves offered by the company")
    # duration: float|None = Field(description="No.of days for which the leave is applied", ge=0.5, le=90.0)
    leave_from: str = Field(description="Date from which the leave starts")    
    leave_upto: str = Field(description="Date on which the leave ends")   
    # coverage_panned: bool|None = Field(description="Ture if another employee is available as a backup")
    assigned_to: str|None = Field(description="Name of the employee who is assiged the responsibilies in the employee's absens")
    


def main():
    init()

    llm = ChatOpenAI(model=model_name, max_completion_tokens=150)

    unstructured_email = """Hi,
    
I am writing to formally request few days of leave, starting from 1-oct-2026 and returning to work on 15-oct-2026. I need this time off to attend to some personal commitments.
Before my leave begins, I will ensure that all my current tasks are up to date. I have also aligned with Naveen Kumar, who has kindly agreed to cover my urgent responsibilities and handle any pressing matters while I am away.
I will have limited access to my email, but you can reach me on my phone at 9731424784 in case of an absolute emergency.
Thank you for considering my request. Please let me know if this timing works or if we need to discuss a handover plan further.
Best regards,

Vinod Kumar Kayartaya
(ID: E0238472)"""

    template = ChatPromptTemplate.from_template(
        "Summarize the leave request in 4 bullet points:\n{leave_request}")

    # chaining of tasks (LCEL, LangChain Expression Language)
    str_chain = template | llm | StrOutputParser()
    parsed_text = str_chain.invoke({"leave_request": unstructured_email})
    print(parsed_text)

    line()

    json_template = ChatPromptTemplate.from_messages([
        ("system", "Extract employee name, phone number, from date, to date, backup assignee  as JSON.\n"
            "Fields of JSON should be: [employee_id, employee_name, employee_phone, leave_from, leave_upto, assigned_to]"),
        ("human", "{leave_request}")
    ])

    # LCEL
    json_chain = json_template | llm | JsonOutputParser()
    json_result = json_chain.invoke({"leave_request": unstructured_email})
    pprint(json_result)     # from pprint import pprint

    line()

    obj_chain = json_template | llm | PydanticOutputParser(pydantic_object=LeaveRequest)
    obj_result = obj_chain.invoke({"leave_request": unstructured_email})
    print(f"{type(obj_result) = }")
    print(obj_result)
    pprint(obj_result.__dict__)

if __name__ == '__main__':
    line()
    main()
    line()
