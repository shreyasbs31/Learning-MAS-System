from datetime import datetime
from google.genai import types
from colours_utils import Colours

def update_interaction_history(session_service, app_name, user_id, session_id, entry):
    try:
        session = session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        interaction_history = session.state.get("interaction_history", []) if session.state else []

        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        interaction_history.append(entry)
        updated_state = session.state.copy() if session.state else {}
        updated_state["interaction_history"] = interaction_history

        # Delete the old session
        session_service.delete_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )

        # Recreate session with updated state
        session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            state=updated_state,
        )
    except Exception as e:
        print(f"Error updating interaction history: {e}")


def add_user_query_to_history(session_service, app_name, user_id, session_id, query):
    update_interaction_history(
        session_service,
        app_name,
        user_id,
        session_id,
        {"action": "user_query", "query": query},
    )


def add_agent_response_to_history(session_service, app_name, user_id, session_id, agent_name, response):
    update_interaction_history(
        session_service,
        app_name,
        user_id,
        session_id,
        {
            "action": "agent_response",
            "agent": agent_name,
            "response": response,
        },
    )

def update_study_progress(session_service, app_name, user_id, session_id, topic: str, percent: int):
    try:
        session = session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        progress = session.state.get("study_progress", [])
            
        # Check if topic already exists
        topic_entry = next((t for t in progress if t["topic"] == topic), None)
        if topic_entry:
            topic_entry["percent"] = percent
            topic_entry["completed"] = percent >= 100
        else:
            topic_entry = {
                "topic": topic,
                "percent": percent,
                "completed": percent >= 100
            }
            progress.append(topic_entry)

        updated_state = session.state.copy()
        updated_state["study_progress"] = progress

        # Update known topics if this topic is completed
        if topic_entry["completed"] and topic not in session.state.get("known_topics", []):
            known = session.state.get("known_topics", [])
            known.append(topic)
            updated_state["known_topics"] = known
            print(f"🎓 Added '{topic}' to known topics as it's now 100% complete.")

        session_service.delete_session(
            app_name=app_name, 
            user_id=user_id, 
            session_id=session_id
        )
        # Recreate session with updated state
        session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            state=updated_state
        )
        print(f"✅ Updated study progress for '{topic}' to {percent}%")
    except Exception as e:
        print(f"❌ Error updating study progress: {e}")


def display_state(session_service, app_name, user_id, session_id, label="Current State"):
    try:
        session = session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        print(f"\n{'-' * 10} {label} {'-' * 10}")
        user_name = session.state.get("user_name", "Unknown")
        print(f"👤 User: {user_name}")

        for key, value in session.state.items():
            if key == "interaction_history":
                continue
            elif key == "study_progress":
                print("📊 Study Progress:")
                if value:
                    for item in value:
                        topic = item.get("topic", "Unknown")
                        percent = item.get("percent", "?")
                        status = "✅" if item.get("completed") else "🟡"
                        color = Colours.GREEN if percent >= 70 else Colours.YELLOW if percent >= 30 else Colours.RED
                        print(f"  - {status} {topic}: {color}{percent}%{Colours.RESET}")
                else:
                    print("  (no progress tracked yet)")
            else:
                print(f"🔑 {key}: {value}")

        interactions = session.state.get("interaction_history", [])
        if interactions:
            print("📝 Interaction History:")
            for i, event in enumerate(interactions[-5:], 1):
                action = event.get("action", "?")
                ts = event.get("timestamp", "?")
                details = event.get("query") or event.get("response") or str(event)
                print(f"  {i}. [{ts}] {action}: {details[:80]}")
        else:
            print("📝 Interaction History: None")

        print("-" * (22 + len(label)))
    except Exception as e:
        print(f"Error displaying state: {e}")


async def process_agent_response(event):
    print(f"Event ID: {event.id}, Author: {event.author}")

    final_response = None
    if event.content and event.content.parts:
        for part in event.content.parts:
            if hasattr(part, "text") and part.text and not part.text.isspace():
                print(f"  Text: '{part.text.strip()}'")

    if event.is_final_response():
        if (
            event.content
            and event.content.parts
            and hasattr(event.content.parts[0], "text")
            and event.content.parts[0].text
        ):
            final_response = event.content.parts[0].text.strip()
            print(f"\n{Colours.BG_BLUE}{Colours.WHITE}{Colours.BOLD}╔══ AGENT RESPONSE ════════════════════{Colours.RESET}")
            print(f"{Colours.CYAN}{Colours.BOLD}{final_response}{Colours.RESET}")
            print(f"{Colours.BG_BLUE}{Colours.WHITE}{Colours.BOLD}╚══════════════════════════════════════{Colours.RESET}\n")
        else:
            print(f"\n{Colours.BG_RED}{Colours.WHITE}Final Agent Response: No text found.{Colours.RESET}\n")

    return final_response


async def call_agent_async(runner, user_id, session_id, query):
    content = types.Content(role="user", parts=[types.Part(text=query)])
    print(f"\n{Colours.BG_GREEN}{Colours.BLACK}{Colours.BOLD}--- Running Query: {query} ---{Colours.RESET}")

    add_user_query_to_history(
    runner.session_service,
    runner.app_name,
    user_id,
    session_id,
    query
    )

    final_response_text = None
    agent_name = None

    try:
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content
        ):
            if event.author:
                agent_name = event.author
            response = await process_agent_response(event)
            if response:
                final_response_text = response
    except Exception as e:
        error_msg = f"ERROR during agent run: {e}"
        print(f"{Colours.BG_RED}{Colours.WHITE}{error_msg}{Colours.RESET}")

        # ✅ Log the error to history so the user sees it later
        add_agent_response_to_history(
            runner.session_service,
            runner.app_name,
            user_id,
            session_id,
            "manager_agent",
            f"[Error] {str(e)}"
        )
        return None

    if final_response_text and agent_name:
        add_agent_response_to_history(
            runner.session_service,
            runner.app_name,
            user_id,
            session_id,
            agent_name,
            final_response_text,
        )

    return final_response_text