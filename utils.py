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
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

def update_interaction_history(session_service, app_name, user_id, session_id, entry):
    try:
        session = session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        history = session.state.get("interaction_history", [])
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history.append(entry)
        session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            state={**session.state, "interaction_history": history},
        )
    except Exception as e:
        print(f"Error updating interaction history: {e}")

def add_user_query_to_history(session_service, app_name, user_id, session_id, query):
    update_interaction_history(session_service, app_name, user_id, session_id, {
        "action": "user_query",
        "query": query,
    })

def add_agent_response_to_history(session_service, app_name, user_id, session_id, agent_name, response):
    update_interaction_history(session_service, app_name, user_id, session_id, {
        "action": "agent_response",
        "agent": agent_name,
        "response": response,
    })

def display_state(session_service, app_name, user_id, session_id, label="Current State"):
    try:
        session = session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        print(f"\n{'-' * 10} {label} {'-' * 10}")
        print(f"👤 User: {session.state.get('user_name', 'Unknown')}")
        print(f"📚 Known Topics: {session.state.get('known_topics', [])}")
        print(f"🎯 Goals: {session.state.get('goals', [])}")
        print("📜 Review Log:")
        review_log = session.state.get("review_log", {})
        if review_log:
            for topic, data in review_log.items():
                print(f"  {topic}: {data}")
        else:
            print("  No entries yet.")
        print("-" * (22 + len(label)))
    except Exception as e:
        print(f"Error displaying state: {e}")

async def process_agent_response(event):
    print(f"Event ID: {event.id}, Author: {event.author}")
    if event.content and event.content.parts:
        for part in event.content.parts:
            if hasattr(part, "text") and part.text:
                print(f"  Text: {part.text.strip()}")

    final_response = None
    if event.is_final_response():
        if (event.content and event.content.parts and hasattr(event.content.parts[0], "text")):
            final_response = event.content.parts[0].text.strip()
            print(f"\n{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}╔══ AGENT RESPONSE ════════════════════════════════{Colors.RESET}")
            print(f"{Colors.CYAN}{Colors.BOLD}{final_response}{Colors.RESET}")
            print(f"{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}╚══════════════════════════════════════════════════{Colors.RESET}\n")
    return final_response

async def call_agent_async(runner, user_id, session_id, query):
    content = types.Content(role="user", parts=[types.Part(text=query)])
    print(f"\n{Colors.BG_GREEN}{Colors.BLACK}{Colors.BOLD}--- Running Query: {query} ---{Colors.RESET}")
    final_response_text = None
    agent_name = None

    display_state(runner.session_service, runner.app_name, user_id, session_id, "State BEFORE")

    try:
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
            if event.author:
                agent_name = event.author
            response = await process_agent_response(event)
            if response:
                final_response_text = response
    except Exception as e:
        print(f"{Colors.BG_RED}{Colors.WHITE}ERROR during agent run: {e}{Colors.RESET}")

    if final_response_text and agent_name:
        add_agent_response_to_history(runner.session_service, runner.app_name, user_id, session_id, agent_name, final_response_text)

    display_state(runner.session_service, runner.app_name, user_id, session_id, "State AFTER")
    print(f"{Colors.YELLOW}{'-' * 30}{Colors.RESET}")
    return final_response_text
