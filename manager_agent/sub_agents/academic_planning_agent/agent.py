from datetime import datetime, timedelta
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from ..search_agent import get_search_tool

# === Tool 1: Add a learning task to the user's schedule ===
def add_task(task: str, due_date: str, tool_context: ToolContext) -> dict:
    """
    Adds a learning task (like 'Read Chapter 3' or 'Revise DP') to the schedule.
    """
    learning_tasks = tool_context.state.get("learning_tasks", [])
    learning_tasks.append({
        "task": task,
        "due_date": due_date,
        "created_at": datetime.now().strftime("%Y-%m-%d")
    })
    tool_context.state["learning_tasks"] = learning_tasks
    return {"message": f"Added task: '{task}' due by {due_date}"}

# === Tool 2: Generate a study plan for the week ===
def generate_schedule(tool_context: ToolContext) -> dict:
    """
    Generates a rough daily plan for the user's tasks over the next 7 days.
    """
    learning_tasks = tool_context.state.get("learning_tasks", [])
    if not learning_tasks:
        return {"message": "No tasks to schedule."}

    plan = {}
    start_date = datetime.now()
    days = 7
    for i, task in enumerate(learning_tasks):
        date = (start_date + timedelta(days=i % days)).strftime("%A")
        plan.setdefault(date, []).append(task["task"])

    return {"weekly_plan": plan}

# === Tool 3: Remove a task (by name) ===
def remove_task(task: str, tool_context: ToolContext) -> dict:
    tasks = tool_context.state.get("learning_tasks", [])
    updated = [t for t in tasks if t["task"] != task]
    tool_context.state["learning_tasks"] = updated
    return {"message": f"Removed task '{task}'"}

# === Tool 4: List all current learning tasks ===
def list_tasks(tool_context: ToolContext) -> dict:
    tasks = tool_context.state.get("learning_tasks", [])
    return {"learning_tasks": tasks}

# === Create the Academic Planning Agent ===
academic_planning_agent = Agent(
    name="academic_planning_agent",
    model="gemini-2.0-flash",
    description="Helps the user create and manage a weekly learning schedule.",
    instruction="""
    You are an academic planning assistant.
    Your job is to:
    - Add, remove, or list study tasks
    - Help the user build a balanced study plan for the week
    - Work with state['learning_tasks'] which contains user's tasks

    Each task is a dictionary with keys: 'task', 'due_date', 'created_at'

    Examples:
    - If the user says "Add DBMS revision on Friday", use the add_task tool
    - If the user says "Remove algebra task", use the remove_task tool
    - If they ask "What's my plan this week?", use generate_schedule

    Never ask the user what they've already told you — use the current state.
    Be proactive in guiding their planning if they seem unsure.
    """,
    tools=[add_task, generate_schedule, remove_task, list_tasks, get_search_tool()],
)