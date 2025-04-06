import asyncio
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from intent_not_identified_flow.tools import Mock_knowledgebase_api

@CrewBase
class IntentCrew:
    """Crew for handling emails with unidentified intent"""
    
    def __init__(self):
        """Simple initialization without yaml dependencies"""
        self._initialized = False
        self._async_lock = asyncio.Lock()
        self._setup_tasks()

    
    # Define agents with direct parameters
    @agent
    def analyzer(self) -> Agent:
        return Agent(
            role="Email Intent Analyzer",
            goal="Analyze emails to determine their intent and whether a general answer can be prepared",
            backstory="You are specialized in understanding customer emails and identifying their needs.",
            llm="anthropic/claude-3-7-sonnet-20250219"
        )
        
    @agent
    def knowledge_retriever(self) -> Agent:
        return Agent(
            role="Knowledge Base Specialist",
            goal="Find relevant information in knowledge bases and documentation",
            backstory="You excel at searching through knowledge repositories to find answers to customer questions.",
            llm="anthropic/claude-3-7-sonnet-20250219",
            tools=[Mock_knowledgebase_api]
        )
        
    @agent
    def content_creator(self) -> Agent:
        return Agent(
            role="Content Creator",
            goal="Create helpful responses and materials based on retrieved information",
            backstory="You craft clear, concise content that addresses customer needs effectively.",
            llm="anthropic/claude-3-7-sonnet-20250219"
        )
        
    @agent
    def summary_specialist(self) -> Agent:
        return Agent(
            role="Summary Specialist",
            goal="Create concise summaries of emails and responses",
            backstory="You distill complex information into clear, actionable summaries.",
            llm="anthropic/claude-3-7-sonnet-20250219"
        )
        
    # Define tasks with explicit parameters
    @task
    def analyze_intent(self) -> Task:
        return Task(
            description="Analyze the incoming email to determine its intent and whether a general answer can be prepared",
            expected_output="Analysis results with determination if we can prepare a general answer"
        )
        
    @task
    def retrieve_information(self) -> Task:
        return Task(
            description="Search knowledge bases to find information relevant to the email inquiry",
            expected_output="Relevant information retrieved from knowledge bases"
        )
        
    @task
    def create_general_answer(self) -> Task:
        return Task(
            description="Create a general answer based on the email inquiry and retrieved information",
            expected_output="A comprehensive response to the customer's inquiry"
        )
        
    @task
    def create_email_summary(self) -> Task:
        return Task(
            description="Create a concise summary of the email content",
            expected_output="A summary highlighting the key points of the email"
        )
        
    @task
    def prepare_final_material(self) -> Task:
        return Task(
            description="Prepare the final materials for handoff to a human agent",
            expected_output="A complete package of materials for the human agent"
        )
    
    def _setup_tasks(self):
        """Just setup tasks without agents for now"""
        tasks = {}
        for task_name in ["analyze_intent", "retrieve_information", "create_general_answer", 
                         "create_email_summary", "prepare_final_material"]:
            task_method = getattr(self, task_name)
            tasks[task_name] = task_method()
        
        # Store tasks without initializing agents yet
        self._tasks = tasks
    
    async def execute_task_async(self, task_name, context):
        """Asynchronous execution of a task with a lazy-loaded agent"""
        # Get the task
        task = self._tasks[task_name]
        
        # Just-in-time agent initialization
        if task_name == "analyze_intent":
            task.agent = self.analyzer()
        elif task_name == "retrieve_information":
            task.agent = self.knowledge_retriever()
        elif task_name in ["create_general_answer", "prepare_final_material"]:
            task.agent = self.content_creator()
        elif task_name == "create_email_summary":
            task.agent = self.summary_specialist()
        
        # Create a single-task crew for this specific task
        mini_crew = Crew(
            agents=[task.agent],
            tasks=[task], 
            process=Process.sequential,
            verbose=True,
        )
        
        # Execute the task
        return await mini_crew.kickoff_async(inputs=context)
    
    
        
    