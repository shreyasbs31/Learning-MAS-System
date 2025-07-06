from google.adk.agents import Agent
from google.adk.tools import google_search

search_prerequisites = Agent(
    name="search_prerequisites",
    model="gemini-2.0-flash",
    description="An agent that searches for prerequisites of a given topic.",
    instruction="""
    You are an agent that searches for prerequisites of a given topic.
    
    When asked about prerequisites:
    1. Use the google_search tool to find the prerequisites for the requested topic.
    2. Provide a list of prerequisite subjects or topics that the user should learn first.
    
    Example response format:
    "To learn <SUBJECT>, you should first understand the following prerequisites:
    1. <PREREQUISITE_1>
    2. <PREREQUISITE_2>
    3. <PREREQUISITE_3>
    
    """,
    
    tools=[google_search],
)