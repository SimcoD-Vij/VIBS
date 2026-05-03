from app.workers.tasks import analyze_session
import sys

session_id = "1122c12a-14a9-44f9-91b6-b085d831a0ec"
print(f"Manually triggering analyze_session for {session_id}...")
# This will run synchronously in this process
analyze_session(session_id)
print("Manual analysis complete!")
