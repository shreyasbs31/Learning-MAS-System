import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import asyncio
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from manager_agent.agent import manager_agent
from utils import call_agent_async, display_state, add_user_query_to_history

load_dotenv()

# Initialize SQLite-based persistent session service
db_url = "sqlite:///./learning_mas.db"
session_service = DatabaseSessionService(db_url=db_url)

APP_NAME = "LearningMAS"
USER_ID = "shreyas"

# Default state structure
initial_state = {
    "user_name": "Shreyas",
    "known_topics": [],
    "learning_tasks": [],
    "review_schedule": [],
    "interaction_history": [],
    "study_progress": [],
}

async def main_async():
    # Check existing sessions
    existing_sessions = session_service.list_sessions(app_name=APP_NAME, user_id=USER_ID)
    if existing_sessions.sessions:
        SESSION_ID = existing_sessions.sessions[0].id
        print(f"Continuing session: {SESSION_ID}")
    else:
        session = session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, state=initial_state
        )
        SESSION_ID = session.id
        print(f"New session created: {SESSION_ID}")

    runner = Runner(
        agent=manager_agent,
        app_name=APP_NAME,
        session_service=session_service
    )

    print("\nWelcome to your Personalized Learning Agent!")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        # Track the user's query in interaction history
        add_user_query_to_history(session_service, APP_NAME, USER_ID, SESSION_ID, user_input)

        # Route the query to the agent
        await call_agent_async(runner, USER_ID, SESSION_ID, user_input)

        # Show updated session state
        display_state(session_service, APP_NAME, USER_ID, SESSION_ID)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()