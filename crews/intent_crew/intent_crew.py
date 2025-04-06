import asyncio
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from intent_not_identified_flow.tools import Mock_knowledgebase_api
import json
from crewai.crews.crew_output import CrewOutput

@CrewBase
class IntentCrew:
    """Crew for handling emails with unidentified intent"""
    
    def __init__(self):
        """Simple initialization without yaml dependencies"""
        self._initialized = False
        self._async_lock = asyncio.Lock()
        self._setup_tasks()

    
    # Define agents with direct parameters - presná replika z YAML
    @agent
    def analyzer(self) -> Agent:
        return Agent(
            role="Intent Analyzer",
            goal="Analyze unclear intents in emails and determine if general information can address the query",
            backstory="You are an expert at analyzing ambiguous requests and determining whether they can be answered with general information or require specific details. You excel at identifying key topics even when the request is vague or unclear.",
            llm="anthropic/claude-3-7-sonnet-20250219"
        )
        
    @agent
    def knowledge_retriever(self) -> Agent:
        return Agent(
            role="Knowledge Retriever",
            goal="Find relevant information from APIs and knowledge bases",
            backstory="You are specialized in querying APIs, databases, and knowledge bases to retrieve the most relevant information for unclear requests. You know how to formulate effective search queries based on limited information and can prioritize search results by relevance.",
            llm="anthropic/claude-3-7-sonnet-20250219",
            tools=[Mock_knowledgebase_api]
        )
        
    @agent
    def content_creator(self) -> Agent:
        return Agent(
            role="Content Creator",
            goal="Create comprehensive, accurate responses based on available information",
            backstory="You excel at crafting helpful responses from either general knowledge or specific information retrieved from knowledge bases. Your writing is clear, informative, and addresses the core questions even when they are implied rather than explicitly stated.",
            llm="anthropic/claude-3-7-sonnet-20250219"
        )
        
    @agent
    def summary_specialist(self) -> Agent:
        return Agent(
            role="Summary Specialist",
            goal="Create concise, accurate summaries of emails and responses",
            backstory="You are skilled at extracting the key points from communication and summarizing them effectively. You can identify the main questions or concerns in an email, even when they're buried in other content. Your summaries are clear, complete, and capture all essential information.",
            llm="anthropic/claude-3-7-sonnet-20250219"
        )
        
    # Define tasks with direct parameters - presná replika z YAML
    @task
    def analyze_intent(self) -> Task:
        return Task(
            description="""
Analyze the incoming email where the intent is not clearly identified.
Determine if we can prepare answers based on general information.

Your task is to:
1. Identify the main topics or questions in the email, even if they're vague
2. Assess whether general information about our products/services would adequately address the email
3. Provide a confidence score for your assessment (0.0 to 1.0)

Input:
Subject: {email_subject}
Body: {email_body}
Sender: {email_sender}
            """,
            expected_output="""
A JSON object with three fields:
- can_prepare_general_answer (boolean): Whether a general answer can be prepared
- identified_topics (array of strings): List of topics identified in the email
- confidence_score (float between 0.0 and 1.0): Your confidence in this assessment
            """,
            agent=self.analyzer()
        )
        
    @task
    def retrieve_information(self) -> Task:
        return Task(
            description="""
Based on the analysis results, query our API and knowledge base to retrieve
relevant information that can help address the request.

Use the identified topics to guide your search and ensure you retrieve
comprehensive information that would help address the vague request.

Analysis results:
{analysis_results}

Original email:
Subject: {email_subject}
Body: {email_body}
Sender: {email_sender}
            """,
            expected_output="""
A comprehensive list of relevant information items retrieved from the knowledge base,
organized by topic and relevance to the query.
            """,
            agent=self.knowledge_retriever()
        )
        
    @task
    def create_general_answer(self) -> Task:
        return Task(
            description="""
Create a comprehensive answer based on the general information retrieved.
Ensure the answer addresses all identified topics and is helpful even without
specific details from the customer.

Your response should:
1. Be friendly and professional
2. Address the topics identified in the analysis
3. Provide useful general information
4. Invite further questions if needed

Retrieved information:
{retrieved_info}

Analysis results:
{analysis_results}

Original email:
{email_content}
            """,
            expected_output="""
A JSON object with three fields:
- summary (string): A brief summary of your response
- detailed_response (string): The complete response to the customer
- references (array of strings): Any references to specific information sources used
            """,
            agent=self.content_creator()
        )
        
    @task
    def create_email_summary(self) -> Task:
        return Task(
            description="""
Create a concise summary of the email content, capturing the essential
points and query, especially since the intent is unclear.

Your summary should:
1. Identify the main request or question
2. Note any specific details provided
3. Highlight any constraints or preferences mentioned
4. Be brief but complete (3-5 bullet points)

Original email:
{email_content}

Created response (if available):
{created_response}
            """,
            expected_output="""
A concise but comprehensive summary of the email content in 3-5 bullet points,
highlighting the main request, specific details, and any constraints mentioned.
            """,
            agent=self.summary_specialist()
        )
        
    @task
    def prepare_final_material(self) -> Task:
        return Task(
            description="""
Prepare a complete package of materials for the handling agent that includes:
1. The original email summary
2. The created response (if available)
3. Reference materials and sources used
4. Suggestions for follow-up questions or clarifications
5. Any additional context that would help the agent understand the situation

This package will be handed off to a human agent who will process the request further.

Email summary:
{email_summary}

Created response (if available):
{created_response}

Retrieved information:
{retrieved_info}

Original email:
{email_content}
            """,
            expected_output="""
A comprehensive package containing the email summary, response (if available),
reference materials, suggested follow-up questions, and additional context
to help the human agent process the request effectively.
            """,
            agent=self.content_creator()
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
        task = self._tasks[task_name]
        print(f"[execute_task_async] Task: {task_name}")
        print(f"[execute_task_async] Original context keys: {list(context.keys())}")

        # Pripravíme slovník inputs pre interpoláciu v CrewAI
        inputs = {}

        for key, value in context.items():
            if key == 'email_content' and isinstance(value, dict):
                inputs['email_subject'] = value.get('subject', 'N/A')
                inputs['email_body'] = value.get('body', 'N/A')
                inputs['email_sender'] = value.get('sender', 'N/A')
                inputs['email_content'] = json.dumps(value, indent=2)
            elif isinstance(value, CrewOutput):
                inputs[key] = value.raw
            elif isinstance(value, dict):
                inputs[key] = json.dumps(value, indent=2)
            elif isinstance(value, list):
                inputs[key] = json.dumps(value, indent=2)
            else:
                inputs[key] = str(value) if value is not None else ""

        print(f"[execute_task_async] Prepared inputs keys for kickoff: {list(inputs.keys())}")
        if 'analysis_results' in inputs:
            print(f"[execute_task_async] analysis_results input sample: {str(inputs['analysis_results'])[:150]}...")
        if 'retrieved_info' in inputs:
            print(f"[execute_task_async] retrieved_info input sample: {str(inputs['retrieved_info'])[:150]}...")
        if 'email_content' in inputs:
             print(f"[execute_task_async] email_content input sample: {str(inputs['email_content'])[:150]}...")
        if 'email_subject' in inputs:
             print(f"[execute_task_async] email_subject input: {inputs['email_subject']}")


        if task_name == "analyze_intent":
            task.agent = self.analyzer()
        elif task_name == "retrieve_information":
            task.agent = self.knowledge_retriever()
        elif task_name in ["create_general_answer", "prepare_final_material"]:
            task.agent = self.content_creator()
        elif task_name == "create_email_summary":
            task.agent = self.summary_specialist()

        mini_crew = Crew(
            agents=[task.agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        print("[execute_task_async] Before kickoff_async")
        try:
            result = await mini_crew.kickoff_async(inputs=inputs)
            print(f"[execute_task_async] After kickoff_async, got result type: {type(result)}")
            if hasattr(result, 'raw'):
                print(f"[execute_task_async] Result sample: {result.raw[:100]}...")
            return result
        except Exception as e:
            print(f"[execute_task_async] EXCEPTION during kickoff_async: {str(e)}")
            print(f"[execute_task_async] EXCEPTION TYPE: {type(e)}")
            original_desc = task._original_description if hasattr(task, '_original_description') else task.description
            print(f"[execute_task_async] TASK description (before interpolation): {original_desc}")
            print(f"[execute_task_async] Inputs passed to kickoff: {inputs}")
            raise
    
    
        
    