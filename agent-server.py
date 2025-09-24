from flask import Flask, render_template, request, redirect, session
import os
from dotenv import load_dotenv

# Add references
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ConnectedAgentTool, MessageRole, ListSortOrder, ToolSet, FunctionTool
from azure.identity import DefaultAzureCredential
from user_functions import user_functions

app = Flask(__name__)

@app.route('/')
def view_form():
    return render_template('hello.html')

@app.route('/handle_post', methods=['POST'])
def handle_post():
    qidFile = request.files['QID']

    if qidFile:
        print(f"Received file: {qidFile.filename}")
        qidFile.save(f"./uploads/{qidFile.filename}")
        create_agent_client(qidFile.filename)

    return render_template('thanks.html', filename=qidFile.filename)

def create_agent_client(filename:str):
    # Function to create and return an agent client
 
    # Load environment variables from .env file
    load_dotenv()
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

    # Connect to the agents client
    agents_client = AgentsClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(
            exclude_environment_credential=True, 
            exclude_managed_identity_credential=True
        ),
    )

    with agents_client:

        functions = FunctionTool(user_functions)
        toolset = ToolSet()
        toolset.add(functions)
        agents_client.enable_auto_function_calls(toolset)

        # Create an agent to triage support ticket processing by using connected agents
        triage_agent_name = "triage-agent"
        triage_agent_instructions = """
        Get the uploaded file contents and file name. Use the connected tools to invoke the content understanding API. Pass the file name and file contents to the API, and get the results.
        """
        
        triage_agent = agents_client.create_agent(
            model=model_deployment,
            name=triage_agent_name,
            instructions=triage_agent_instructions,
            toolset=toolset
        )

        # Use the agents to triage a support issue
        print("Creating agent thread.")
        thread = agents_client.threads.create()  

        # Create the ticket prompt
        prompt = '{"fileName": ' + filename + ' "fileConents": "abc23423242342"}'
        print(f"Prompt: {prompt}")

            
        # Send a prompt to the agent
        message = agents_client.messages.create(
            thread_id=thread.id,
            role=MessageRole.USER,
            content=prompt,
        ) 
            
        # Run the thread usng the primary agent
        print("\nProcessing agent thread. Please wait.")
        run = agents_client.runs.create_and_process(thread_id=thread.id, agent_id=triage_agent.id)
                
        if run.status == "failed":
            print(f"Run failed: {run.last_error}")

        # Fetch and display messages
        messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
        for message in messages:
            if message.text_messages:
                last_msg = message.text_messages[-1]
                print(f"{message.role}:\n{last_msg.text.value}\n")

        # Clean up
        print("Cleaning up agents:")
        agents_client.delete_agent(triage_agent.id)
        print("Deleted triage agent.")

if __name__ == '__main__':
    app.run()