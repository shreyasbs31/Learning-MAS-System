from datetime import datetime, timedelta
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext

# === Tool 1: Record a review result and apply SM-2 logic ===
def record_review_result(topic: str, score: int, tool_context: ToolContext) -> dict:
    """
    Record a spaced repetition result using SM-2 algorithm.
    score: integer between 0–5 (5 = perfect recall, 0 = complete blackout)
    """
    schedule = tool_context.state.get("review_schedule", [])
    today = datetime.now().date()
    topic_entry = next((t for t in schedule if t["topic"] == topic), None)

    if not topic_entry:
        topic_entry = {
            "topic": topic,
            "last_reviewed": str(today),
            "next_review_due": str(today + timedelta(days=1)),
            "interval": 1,
            "repetition": 1,
            "easiness": 2.5,
            "history": [],
        }
        schedule.append(topic_entry)

    if score < 3:
        topic_entry["repetition"] = 0
        topic_entry["interval"] = 1
    else:
        topic_entry["repetition"] += 1
        if topic_entry["repetition"] == 1:
            topic_entry["interval"] = 1
        elif topic_entry["repetition"] == 2:
            topic_entry["interval"] = 6
        else:
            topic_entry["interval"] = int(
                round(topic_entry["interval"] * topic_entry["easiness"])
            )

        # Update easiness factor
        ef = topic_entry["easiness"]
        ef += 0.1 - (5 - score) * (0.08 + (5 - score) * 0.02)
        topic_entry["easiness"] = max(1.3, ef)

    topic_entry["last_reviewed"] = str(today)
    topic_entry["next_review_due"] = str(today + timedelta(days=topic_entry["interval"]))
    topic_entry["history"].append({"date": str(today), "score": score})

    tool_context.state["review_schedule"] = schedule
    return {
        "message": f"Review recorded for '{topic}' with score {score}. Next review in {topic_entry['interval']} days."
    }

# === Tool 2: Get topics due for review today ===
def get_due_reviews(tool_context: ToolContext) -> dict:
    today = datetime.now().date()
    schedule = tool_context.state.get("review_schedule", [])
    due = [t["topic"] for t in schedule if datetime.strptime(t["next_review_due"], "%Y-%m-%d").date() <= today]
    return {"due_topics": due}

# === Tool 3: View review history for a topic ===
def view_review_history(topic: str, tool_context: ToolContext) -> dict:
    schedule = tool_context.state.get("review_schedule", [])
    topic_entry = next((t for t in schedule if t["topic"] == topic), None)
    if topic_entry:
        return {"history": sorted(topic_entry["history"], key=lambda x: x["date"], reverse=True)}
    return {"message": f"No review history found for '{topic}'"}

# === Tool 4: Reset spaced repetition progress for a topic ===
def reset_schedule(topic: str, tool_context: ToolContext) -> dict:
    schedule = tool_context.state.get("review_schedule", [])
    for entry in schedule:
        if entry["topic"] == topic:
            entry.update({
                "repetition": 0,
                "interval": 1,
                "easiness": 2.5,
                "next_review_due": str(datetime.now().date() + timedelta(days=1)),
                "history": []
            })
            break
    tool_context.state["review_schedule"] = schedule
    return {"message": f"Reset review progress for '{topic}'"}

# === Tool 5: List all topics in the review schedule ===
def list_reviewed_topics(tool_context: ToolContext) -> dict:
    schedule = tool_context.state.get("review_schedule", [])
    return {"topics": [t["topic"] for t in schedule]}

# === Create the Spaced Repetition Agent ===
spaced_repetition_agent = Agent(
    name="spaced_repetition_agent",
    model="gemini-2.0-flash",
    description="Manages spaced repetition and memory tracking for learning topics.",
    instruction="""
    You are a spaced repetition memory coach.
    Your job is to:
    - Tell users what to review today
    - Record results from reviews (score 0–5)
    - If user doesn't give a review, ask them to do so
    - Maintain and update the review schedule in state['review_schedule'] using SM-2 logic
    - If user asks to review a topic which isn't on his 'known_topics' or his 'review_schedule', tell them that they need to first learn it, and only then can they review it. 
    - If user asks to reset a topic, reset its review progress
    - If user asks to view review history, show them the history of scores for that topic

    Score meanings:
    - 5: Perfect recall
    - 4: Minor hesitation
    - 3: Took effort
    - 2: Hard to remember
    - 1: Barely recalled
    - 0: Completely forgot

    Use 'record_review_result(topic, score)' to update a topic.
    Use 'get_due_reviews' to show what to revise today.
    """,
    tools=[
        record_review_result,
        get_due_reviews,
        view_review_history,
        reset_schedule,
        list_reviewed_topics
    ],
)