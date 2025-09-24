from flask import Flask, render_template, request, redirect, session
import os
from dotenv import load_dotenv

# Add references
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ConnectedAgentTool, MessageRole, ListSortOrder, ToolSet, FunctionTool
from azure.identity import DefaultAzureCredential

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
        create_agent_client()

    username = request.form.get('username')
    password = request.form.get('password')
    return render_template('thanks.html', filename=qidFile.filename)

def create_agent_client():
    # Function to create and return an agent client
 
    # Load environment variables from .env file
    load_dotenv()
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

    print(f"Project Endpoint: {project_endpoint}")
    print(f"Model Deployment: {model_deployment}")

    # Connect to the agents client
    agents_client = AgentsClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(
            exclude_environment_credential=True, 
            exclude_managed_identity_credential=True
        ),
    )

    with agents_client:
        # Create an agent to extract content from documents. 
        doc_handling_agent_name = "doc_handling_agent"
        doc_handling_agent_instructions = """
        Assess how urgent a ticket is based on its description.

        Respond with one of the following levels:
        - High: User-facing or blocking issues
        - Medium: Time-sensitive but not breaking anything
        - Low: Cosmetic or non-urgent tasks

        Only output the urgency level and a very brief explanation.
        """

        doc_handling_agent = agents_client.create_agent(
            model=model_deployment,
            name=doc_handling_agent_name,
            instructions=doc_handling_agent_instructions
        )

        # Create connected agent tools for the support agents
        doc_handling_agent_tool = ConnectedAgentTool(
            id=doc_handling_agent.id, 
            name=doc_handling_agent_name, 
            description="Assess the priority of a ticket"
        )

            # Create an agent to triage support ticket processing by using connected agents
        triage_agent_name = "triage-agent"
        triage_agent_instructions = """
        Triage the given ticket. Use the connected tools to determine the ticket's priority, 
        which team it should be assigned to, and how much effort it may take.
        """
        
        triage_agent = agents_client.create_agent(
            model=model_deployment,
            name=triage_agent_name,
            instructions=triage_agent_instructions,
            tools=[
                doc_handling_agent_tool.definitions[0]
            ]
        )

        # Use the agents to triage a support issue
        print("Creating agent thread.")
        thread = agents_client.threads.create()  

        # Create the ticket prompt
        prompt = '{"ticket_id": "12345", "description": "The application crashes when I try to upload a file. This is preventing me from completing my work and needs immediate attention."}'
            
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
        agents_client.delete_agent(doc_handling_agent.id)
        print("Deleted document handling agent.")

if __name__ == '__main__':
    app.run()