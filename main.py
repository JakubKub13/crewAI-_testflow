import os
import asyncio
import logging
from pydantic import BaseModel

from crewai.flow import Flow, listen, start, router

from intent_not_identified_flow.crews.intent_crew.intent_crew import IntentCrew
from intent_not_identified_flow.models.email import EmailContent

# Konfigurácia loggingu pre produkčné prostredie
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print('I am here')

class IntentState(BaseModel):
    """State model for the intent not identified flow"""
    email: EmailContent = None
    analysis_results: dict = None
    retrieved_info: dict = None
    created_response: dict = None
    email_summary: str = ""
    final_materials: dict = None
    can_prepare_info: bool = False

class IntentNotIdentifiedFlow(Flow[IntentState]):
    """Flow for handling emails with unidentified intent - follows the diagram exactly"""
    
    
    # Creates a new IntentCrew instance without singleton pattern
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print('Creating IntentCrew')
        self.intent_crew = IntentCrew()
        print('IntentCrew created')
    
    
    @start()
    async def intent_not_identified(self):
        """Starting point - intent not identified"""
        logger.info("Starting flow: Intent not identified")
        # Email should be set before kickoff
        if not self.state.email:
            raise ValueError("Email must be set before starting the flow")
    
    @listen(intent_not_identified)
    async def text_analysis_general_info(self):
        """Text analysis if we can prepare answers based on general info"""
        logger.info("Text analysis if we can prepare answers based on general info")
        
        try:
            print('Before execute_task_async for analyze_intent')
            analysis_output = await self.intent_crew.execute_task_async(
                "analyze_intent",
                context={"email_content": self.state.email.dict()}
            )
            print('After execute_task_async for analyze_intent')
            
            # Uložíme celý výstup pre prípadné ďalšie použitie
            self.state.analysis_results = {
                "raw": analysis_output.raw
            }
            
            # Pokúsime sa extrahovať JSON z výstupu, ktorý by mal byť v JSON formáte
            import json
            try:
                # Hľadáme JSON v texte - agenti často vracajú JSON v texte
                import re
                json_pattern = r'\{.*\}'
                json_match = re.search(json_pattern, analysis_output.raw, re.DOTALL)
                
                if json_match:
                    analysis_json = json.loads(json_match.group(0))
                    self.state.analysis_results.update(analysis_json)
                    self.state.can_prepare_info = analysis_json.get("can_prepare_general_answer", False)
                else:
                    # Ak sa nenájde JSON, použijeme heuristiku z textu
                    self.state.can_prepare_info = "can prepare general answer: true" in analysis_output.raw.lower() or "can_prepare_general_answer: true" in analysis_output.raw.lower()
                    
            except json.JSONDecodeError:
                # Ak sa nepodari parsovať JSON, použijeme jednoduchú heuristiku
                self.state.can_prepare_info = "can prepare general answer: true" in analysis_output.raw.lower() or "can_prepare_general_answer: true" in analysis_output.raw.lower()
            
            logger.info(f"Analysis complete. Can prepare general info: {self.state.can_prepare_info}")
            
        except Exception as e:
            logger.error(f"Error during text analysis: {str(e)}")
            # Fail gracefully in production
            self.state.can_prepare_info = False
            raise
        
    @listen(text_analysis_general_info)
    async def decision_prepare_info(self):
        """Decision: Able to prepare info?"""
        logger.info(f"Decision: {'Able' if self.state.can_prepare_info else 'Unable'} to prepare info")
    
    @router(decision_prepare_info)
    async def route_based_on_decision(self):
        """Router to direct flow based on analysis decision"""
        if self.state.can_prepare_info:
            return "can_prepare_info"
        else:
            return "cannot_prepare_info"
    
    @listen("can_prepare_info")
    async def api_knowledge_base_finding(self):
        """API web/knowledge base - finding the info"""
        logger.info("API web/knowledge base - finding the info")
        
        try:
            # Využitie asynchrónneho rozhrania IntentCrew
            info = await self.intent_crew.execute_task_async(
                "retrieve_information",
                context={
                    "email_content": self.state.email.dict(),
                    "analysis_results": self.state.analysis_results
                }
            )
            
            self.state.retrieved_info = info
            logger.info("API/knowledge base search complete")
        except Exception as e:
            logger.error(f"Error during information retrieval: {str(e)}")
            # Fail gracefully in production
            self.state.retrieved_info = {"error": "Failed to retrieve information"}
            raise
        
    @listen(api_knowledge_base_finding)
    async def creating_answer_general_info(self):
        """Creating answer based on general info"""
        logger.info("Creating answer based on general info")
        
        try:
            # Využitie asynchrónneho rozhrania IntentCrew
            response = await self.intent_crew.execute_task_async(
                "create_general_answer",
                context={
                    "email_content": self.state.email.dict(),
                    "analysis_results": self.state.analysis_results,
                    "retrieved_info": self.state.retrieved_info
                }
            )
            
            self.state.created_response = response
            logger.info("General answer created")
        except Exception as e:
            logger.error(f"Error during answer creation: {str(e)}")
            # Fail gracefully
            self.state.created_response = {"error": "Failed to create answer"}
            raise
        
    @listen(creating_answer_general_info)
    async def drafting_summary_from_answer(self):
        """Drafting a summary from answer"""
        logger.info("Drafting a summary from answer")
        
        try:
            # Využitie asynchrónneho rozhrania IntentCrew
            summary = await self.intent_crew.execute_task_async(
                "create_email_summary",
                context={
                    "email_content": self.state.email.dict(),
                    "created_response": self.state.created_response
                }
            )
            
            self.state.email_summary = summary
            logger.info("Summary from answer drafted")
            return "summary_created"
        except Exception as e:
            logger.error(f"Error during summary creation: {str(e)}")
            # Fail gracefully
            self.state.email_summary = "Failed to create summary from answer"
            return "summary_created"  # Still proceed to next step
    
    @listen("cannot_prepare_info")
    async def creating_summary_from_email(self):
        """Creating a summary from email"""
        logger.info("Creating a summary from email")
        
        try:
            # Využitie asynchrónneho rozhrania IntentCrew
            summary = await self.intent_crew.execute_task_async(
                "create_email_summary",
                context={"email_content": self.state.email.dict()}
            )
            
            self.state.email_summary = summary
            logger.info("Email summary created")
            return "summary_created"
        except Exception as e:
            logger.error(f"Error during email summary creation: {str(e)}")
            # Fail gracefully
            self.state.email_summary = "Failed to create summary from email"
            return "summary_created"  # Still proceed to next step
        
    @listen("summary_created")
    async def switching_to_agent_with_materials(self):
        """Switching to an agent with a pre-prepared material for the processed part"""
        logger.info("Switching to an agent with a pre-prepared material for the processed part")
        
        try:
            # Využitie asynchrónneho rozhrania IntentCrew
            materials = await self.intent_crew.execute_task_async(
                "prepare_final_material",
                context={
                    "email_content": self.state.email.dict(),
                    "email_summary": self.state.email_summary,
                    "created_response": self.state.created_response,
                    "retrieved_info": self.state.retrieved_info
                }
            )
            
            self.state.final_materials = materials
            logger.info("Flow complete - materials prepared for agent handoff!")
            return materials
        except Exception as e:
            logger.error(f"Error during final material preparation: {str(e)}")
            # Fail gracefully
            self.state.final_materials = {"error": "Failed to prepare final materials"}
            return self.state.final_materials

async def async_kickoff():
    """Start the intent not identified flow with a mock email (async version)"""
    # Set your API key (or use from environment)
    if "ANTHROPIC_API_KEY" not in os.environ:
        logger.warning("ANTHROPIC_API_KEY not found in environment, using default value")
    
    # Create mock email with unclear intent
    mock_email = EmailContent(
        subject="Question about your product",
        body="""
        Hello,
        
        I came across your company online and I'm interested in learning more.
        I'm not entirely sure if your services would be a good fit for what I need,
        but I'd like to understand what options might be available.
        
        Could you provide me with some general information?
        
        Thanks,
        John
        """,
        sender="john.doe@example.com"
    )
    
    # Initialize flow with email - with additional logging
    print('Creating IntentNotIdentifiedFlow')
    flow = IntentNotIdentifiedFlow()
    flow.state.email = mock_email
    print('Email set in state')
    
    try:
        # Kickoff the flow asynchronously
        print('Before kickoff_async')
        result = await flow.kickoff_async()
        print('After kickoff_async')
        
        logger.info("\n--- Flow Execution Complete ---")
        logger.info(f"Final materials prepared: {result}")
        
        return result
    except Exception as e:
        logger.error(f"Error during flow execution: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    asyncio.run(async_kickoff())



    


