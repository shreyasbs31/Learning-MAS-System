# agents/search_agent.py
from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool

search_agent = Agent(
    name="search_agent",
    model="gemini-2.0-flash",
    description="An agent that performs reliable web searches and returns helpful summaries.",
    instruction="""
    You are a helpful research assistant.
    Always use the `google_search` tool to find answers to queries.
    Search the web, then summarize the most relevant information.
    Do not hallucinate or make up answers.
    If search results are unclear, say so and suggest rephrasing or narrowing the question.
    """,
    tools=[google_search],
)

# Register as AgentTool for other agents to use
search_tool = AgentTool(search_agent)

def get_search_tool():
    return search_tool

# Optional: utility function for delegation
async def search_for_prereqs(topic: str, tool_context) -> list[str]:
    try:
        result = await tool_context.call_tool(search_tool, input=f"What are the prerequisites to learn {topic}?")
        return [result] if isinstance(result, str) else result
    except Exception as e:
        return [f"Error searching: {e}"]
    
