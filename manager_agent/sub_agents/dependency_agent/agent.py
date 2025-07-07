# sub_agents/dependency_agent/agent.py
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from ..search_agent import get_search_tool, search_for_prereqs

# === Tool 1: Add a prerequisite ===
def add_prerequisite(topic: str, required: str, tool_context: ToolContext) -> dict:
    prereqs = tool_context.state.get("prereq_map", {})
    prereqs.setdefault(topic, [])
    if required not in prereqs[topic]:
        prereqs[topic].append(required)
    tool_context.state["prereq_map"] = prereqs
    return {"message": f"Added prerequisite: '{required}' → '{topic}'"}

# === Tool 2: Remove a prerequisite ===
def remove_prerequisite(topic: str, prereq: str, tool_context: ToolContext) -> dict:
    prereqs = tool_context.state.get("prereq_map", {})
    prereqs.setdefault(topic, [])
    if prereq in prereqs[topic]:
        prereqs[topic].remove(prereq)
    tool_context.state["prereq_map"] = prereqs
    return {"message": f"Removed '{prereq}' from prerequisites of '{topic}'"}

# === Tool 3: Check if user can learn a topic ===
def can_learn(topic: str, tool_context: ToolContext) -> dict:
    prereqs = tool_context.state.get("prereq_map", {})
    known = set(tool_context.state.get("known_topics", []))
    required = set(prereqs.get(topic, []))
    return {
        "can_learn": required.issubset(known),
        "missing": list(required - known),
    }

# === Tool 4: Mark topic as learned ===
def learned(topic: str, tool_context: ToolContext) -> dict:
    known = set(tool_context.state.get("known_topics", []))
    known.add(topic)
    tool_context.state["known_topics"] = list(known)
    return {"message": f"Marked '{topic}' as learned."}

# === Tool 5: Forget a topic ===
def forget(topic: str, tool_context: ToolContext) -> dict:
    known = set(tool_context.state.get("known_topics", []))
    known.discard(topic)
    tool_context.state["known_topics"] = list(known)
    return {"message": f"Forgot topic '{topic}'."}

# === Tool 6: List known topics ===
def list_known(tool_context: ToolContext) -> dict:
    return {"known_topics": tool_context.state.get("known_topics", [])}

# === Tool 7: List prerequisites for a topic ===
def get_prereqs(topic: str, tool_context: ToolContext) -> dict:
    prereqs = tool_context.state.get("prereq_map", {})
    return {"prerequisites": prereqs.get(topic, [])}

# === Tool 8: Suggest next topics based on what's learnable ===
def suggest_next_topics(tool_context: ToolContext) -> dict:
    prereqs = tool_context.state.get("prereq_map", {})
    known = set(tool_context.state.get("known_topics", []))
    suggestions = []
    for topic, required in prereqs.items():
        if topic not in known and set(required).issubset(known):
            suggestions.append(topic)
    return {"suggestions": suggestions}

# === Tool 9: Automatically update prereqs using Search Agent ===
async def auto_update_prereqs(topic: str, tool_context: ToolContext) -> dict:
    try:
        guesses = await search_for_prereqs(topic, tool_context)
        prereqs = tool_context.state.get("prereq_map", {})
        prereqs.setdefault(topic, [])
        for guess in guesses:
            if guess not in prereqs[topic]:
                prereqs[topic].append(guess)
        tool_context.state["prereq_map"] = prereqs
        return {"message": f"Inferred prerequisites for '{topic}':", "suggested": prereqs[topic]}
    except Exception as e:
        return {"message": f"Search failed. Please manually add prerequisites for '{topic}'. Error: {e}"}

# === Create the Dependency Agent ===
dependency_agent = Agent(
    name="dependency_agent",
    model="gemini-2.0-flash",
    description="Helps users understand and navigate topic dependencies",
    instruction="""
    You are a learning path architect.
    Maintain two state objects:
    - prereq_map: { topic: [prerequisite1, prerequisite2] }
    - known_topics: [list of things user already knows]

    Use tools to:
    - Tell users if they can learn something
    - Suggest what's ready to be learned
    - Add/remove prerequisites
    - Remember what the user has learned or forgotten
    - Automatically infer dependencies via web search

    Never hardcode dependencies — evolve them based on user feedback.
    If you can't find a dependency, ask the user directly.
    """,
    tools=[
        add_prerequisite,
        remove_prerequisite,
        can_learn,
        learned,
        forget,
        list_known,
        get_prereqs,
        suggest_next_topics,
        auto_update_prereqs,
        get_search_tool()
    ],
)
