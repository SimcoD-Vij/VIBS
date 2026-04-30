from app.workers.tasks import analyze_session
import sys

if __name__ == "__main__":
    session_id = "0f5be2fd-2aae-4237-bfff-95a76cafd98b"
    print(f"Triggering analyze_session for {session_id}...")
    analyze_session.delay(session_id)
    print("Task enqueued.")
