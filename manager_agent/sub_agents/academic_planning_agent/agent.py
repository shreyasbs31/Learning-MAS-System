from datetime import datetime, timedelta
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from ..search_agent import get_search_tool

# === Tool 1: Add a learning task to the user's schedule ===
def add_task(task: str, due_date: str, tool_context: ToolContext) -> dict:
    """
    Adds a learning task (like 'Read Chapter 3' or 'Revise DP') to the schedule.
    """
    try:
        datetime.strptime(due_date, "%d-%m-%Y")
    except ValueError:
        return {"message": "❌ Invalid date format. Please use DD-MM-YYYY."}

    learning_tasks = tool_context.state.get("learning_tasks", [])
    
    if any(t["task"].lower() == task.lower() for t in learning_tasks):
        return {"message": f"⚠️ Task '{task}' already exists."}

    learning_tasks.append({
        "task": task,
        "due_date": due_date,
        "created_at": datetime.now().strftime("%d-%m-%Y"),
    })
    tool_context.state["learning_tasks"] = learning_tasks
    return {"message": f"✅ Added task: '{task}' due by {due_date}"}

# === Tool 2: Generate a study plan for the week ===
def generate_schedule(tool_context: ToolContext) -> dict:
    """
    Generates a smart weekly study plan by sorting tasks by due date.
    Filters out tasks with invalid or missing due dates.
    """
    learning_tasks = tool_context.state.get("learning_tasks", [])
    if not learning_tasks:
        return {"message": "No tasks to schedule."}

    # Validate due_date formats and filter valid tasks
    valid_tasks = []
    for t in learning_tasks:
        try:
            datetime.strptime(t["due_date"], "%d-%m-%Y")
            valid_tasks.append(t)
        except (ValueError, KeyError):
            continue  # Skip if due_date is invalid or missing

    if not valid_tasks:
        return {"message": "❌ All tasks have invalid or missing due dates."}

    # Sort valid tasks by due date
    sorted_tasks = sorted(
        valid_tasks,
        key=lambda t: datetime.strptime(t["due_date"], "%d-%m-%Y")
    )

    # Build weekly plan with pretty formatting
    plan = {}
    start_date = datetime.now().date()
    for i, task in enumerate(sorted_tasks):
        day = (start_date + timedelta(days=i)).strftime("%A, %b %d")
        plan.setdefault(day, []).append(f"{task['task'].capitalize()} (Due: {task['due_date']})")

    pretty_output = "\n".join(
        f"\n📅 {day}:\n" + "\n".join(f"  {item}" for item in items)
        for day, items in plan.items()
    )

    return {"weekly_plan": pretty_output}

# === Tool 3: Remove a task (by name) ===
def remove_task(task: str, tool_context: ToolContext) -> dict:
    tasks = tool_context.state.get("learning_tasks", [])
    updated = [t for t in tasks if t["task"].lower() != task.lower()]
    tool_context.state["learning_tasks"] = updated
    return {"message": f"Removed task '{task}'"}

# === Tool 4: List all current learning tasks ===
def list_tasks(tool_context: ToolContext) -> dict:
    tasks = tool_context.state.get("learning_tasks", [])
    if not tasks:
        return {"message": "📭 You have no current learning tasks."}
    
    formatted = [
        f"📌 {t['task'].capitalize()} (🗓 Due: {t['due_date']})"
        for t in sorted(tasks, key=lambda x: datetime.strptime(x["due_date"], "%d-%m-%Y"))
    ]
    return {"learning_tasks": formatted}

# === Tool 5: Update study progress for a topic ===
def update_study_progress(topic: str, percent: int, completed: bool = False, tool_context=None) -> dict:
    progress = tool_context.state.get("study_progress", [])
    known_topics = tool_context.state.get("known_topics", [])

    # Check if topic already exists in progress
    entry = next((item for item in progress if item["topic"] == topic), None)

    if entry:
        entry.update({
            "percent": percent,
            "completed": completed
        })
    else:
        progress.append({
            "topic": topic.capitalize(),
            "percent": percent,
            "completed": completed
        })

    # Auto-sync to known_topics if completed and not already present
    if percent == 100 and topic not in known_topics:
        known_topics.append(topic)

    tool_context.state["study_progress"] = progress
    tool_context.state["known_topics"] = known_topics

    return {
        "message": f"Progress updated for '{topic}': {percent}% {'✅ (completed & added to known topics)' if percent == 100 else ''}"
    }

# === Tool 6: Suggest next topic based on study progress ===
def suggest_next_topic(tool_context) -> dict:
    progress = tool_context.state.get("study_progress", [])
    pending = [t for t in progress if not t["completed"]]
    pending_sorted = sorted(pending, key=lambda t: t["percent"])
    if pending_sorted:
        return {"next_topic": pending_sorted[0]["topic"]}
    return {"message": "All topics completed!"}



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
    If user asks for help with unfamiliar concepts or wants to explore a new topic, use the web search tool.

    - If the user mentions study progress like "I finished 80% of Graphs", extract:
    - topic: "Graphs"
    - percent: 80
    - completed: True if percent == 100 else False
    Then call the tool `update_study_progress` with all three parameters: topic, percent, and completed.
    """,
    tools=[add_task, generate_schedule, remove_task, list_tasks, update_study_progress, suggest_next_topic, get_search_tool()],
)