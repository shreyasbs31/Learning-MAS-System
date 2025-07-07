from datetime import datetime
from google.genai import types

# ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_BLUE = "\033[44m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"


def update_interaction_history(session_service, app_name, user_id, session_id, entry):
    try:
        session = session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        interaction_history = session.state.get("interaction_history", [])

        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        interaction_history.append(entry)
        updated_state = session.state.copy()
        updated_state["interaction_history"] = interaction_history

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

        keys = [k for k in session.state if k != "interaction_history"]
        for key in keys:
            print(f"🔑 {key}: {session.state[key]}")

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
            print(f"\n{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}╔══ AGENT RESPONSE ════════════════════{Colors.RESET}")
            print(f"{Colors.CYAN}{Colors.BOLD}{final_response}{Colors.RESET}")
            print(f"{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}╚══════════════════════════════════════{Colors.RESET}\n")
        else:
            print(f"\n{Colors.BG_RED}{Colors.WHITE}Final Agent Response: No text found.{Colors.RESET}\n")

    return final_response


async def call_agent_async(runner, user_id, session_id, query):
    content = types.Content(role="user", parts=[types.Part(text=query)])
    print(f"\n{Colors.BG_GREEN}{Colors.BLACK}{Colors.BOLD}--- Running Query: {query} ---{Colors.RESET}")
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
        print(f"{Colors.BG_RED}{Colors.WHITE}ERROR during agent run: {e}{Colors.RESET}")

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