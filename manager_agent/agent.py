from google.adk.agents import Agent

from .sub_agents.academic_planning_agent.agent import academic_planning_agent
from .sub_agents.spaced_repetition_agent.agent import spaced_repetition_agent
from .sub_agents.dependency_agent.agent import dependency_agent

manager_agent = Agent(
    name="manager_agent",
    model="gemini-2.0-flash",
    description="Main manager agent that routes queries to sub-agents handling spaced repetition, planning, and learning dependencies.",
    instruction="""
    You are the root agent managing a personalized learning assistant.
    Your job is to:
    - Understand the user's academic and learning-related queries
    - Delegate the task to the appropriate sub-agent:
        - Academic planning: schedule study sessions and deadlines
        - Spaced repetition: manage review timing and memory tracking
        - Dependency engine: determine if a topic can be learned based on known topics
    - Always route the query to the most suitable agent.

    IMPORTANT:
    - Use the session state (`known_topics`, `learning_tasks`, `review_schedule`) to inform decisions.
    - You can summarize or reflect, but deeper logic should be done by the delegated sub-agent.

    Example Routing:
    - "What should I revise today?" → spaced_repetition_agent
    - "Help me make a weekly plan to study algorithms" → academic_planning_agent
    - "Can I learn Dynamic Programming now?" → dependency_agent
    """,
    sub_agents=[
        academic_planning_agent,
        spaced_repetition_agent,
        dependency_agent,
    ],
    tools=[],
)