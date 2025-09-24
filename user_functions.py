import json
from pathlib import Path
import uuid
from typing import Any, Callable, Set

# Create a function to submit a support ticket
def submit_support_ticket(file_name: str, file_contents: str) -> str:
    
     print(file_name)
     print(file_contents)
     message_json = json.dumps({"message": f"The ticket file is saved as {file_name}, file contents: {file_contents}"})
     return message_json

# Define a set of callable functions
user_functions: Set[Callable[..., Any]] = {
     submit_support_ticket
 }

