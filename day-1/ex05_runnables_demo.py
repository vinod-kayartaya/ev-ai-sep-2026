import os
import sys

from myutils import line
from dotenv import load_dotenv
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnableLambda

def init():
    global model_name
    load_dotenv()   # loads environment variables from .env file
    model_name = os.environ.get("OPENAI_MODEL_NAME")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required, but missing!")
        sys.exit(1)


def sanitize_incident_inputs(report):
    """Preprocessing the input to the chains (ECLC)"""
    return {
        "report_id": report.get("report_id", "ID-UNKNOWN"),
        "allegation_type": report.get("allegation_type", "GENERAL"),
        "department_name": report.get("department_name", "Unspecified"),
        "incidence_summary": report.get("incidence_summary", ""),
        "employee_name": report.get("employee_name"),
        "incident_timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S.%s')
    }


def main():
    init()

    llm = ChatOpenAI(model=model_name)

    compliance_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an Employee Law Compliance Auditor for Amazone Global. "
            "Draft a formal, confidential investigation memo/email outlining required statutory actions, "
            "anti-retaliatory protection, and next investigative interviews etc."),
        ("human", "Incident details:\n"
            "Case: {report_id} ({allegation_type})\n"
            "Department: {department_name}\n"
            "Incident summary: {incidence_summary}\n"
            "Incident at: {incident_timestamp}")
    ])
    
    emp_support_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a people operations employee care specialist. "
            "Draft a empathatic, professional confirmation letter akcnowledging the receipt of complaint, "
            "affirming complete support and confidentiality along with anti-retaliatory protection and offering councelling."),
        ("human", "Case: {report_id}\nDepartment: {department_name}\nSubmitted by: {employee_name}")
    ])

    # more than one ECEL chains (to be run in parallel)
    compliance_chain = compliance_prompt | llm | StrOutputParser()
    emp_support_chain = emp_support_prompt | llm | StrOutputParser()

    parallel_pipeline = RunnableParallel(
        compliance_memo=compliance_chain,
        emp_support_memo=emp_support_chain
    )


    report_data = {
        "report_id": "ASD-949-283AB",
        "allegation_type": "EMPLOYEE_CONDUCT",
        "department_name": "Accounting",
        "incidence_summary": "Employee reported safety violation in the office during office hours, after which the manager removed the employee from the current project.",
        "employee_name": "John Doe"
    }


    final_pipeline = RunnableLambda(sanitize_incident_inputs) | parallel_pipeline

    resp = final_pipeline.invoke(report_data)


    print("Compliance memo: ")
    print("=================")
    print(resp["compliance_memo"])
    line()

    print("Employee support memo: ")
    print("=======================")
    print(resp["emp_support_memo"])



if __name__ == '__main__':
    line()
    main()
    line()
