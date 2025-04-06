from crewai.tools import tool
from intent_not_identified_flow.services.knowledge_api import KnowledgeAPI

# Tool creation
@tool("Mock_knowledgebase_api")
def Mock_knowledgebase_api(query: str) -> str:
    """Search the knowledge base for relevant information based on the given query.
    
    Args:
        query: The search query string to look for in the knowledge base
        
    Returns:
        List of search results with relevant information
    """
    knowledge_api = KnowledgeAPI()
    return knowledge_api.search(query)
