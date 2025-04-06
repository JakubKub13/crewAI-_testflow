from typing import Dict, List, Any

class KnowledgeAPI:
    """Mock API service for knowledge retrieval"""
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Mock API that returns knowledge base results
        
        Args:
            query: The search query string
            
        Returns:
            List of search results with title and content
        """
        print(f"Searching knowledge base for: {query}")
        
        # Mock data - in production, replace with actual API integration
        results = [
            {
                "title": "Product Information", 
                "content": "Our product is a comprehensive customer service solution that combines AI-driven analytics with human-centered design. It features a unified dashboard, real-time data processing, custom reporting tools, and seamless integration with existing systems."
            },
            {
                "title": "Pricing Structure", 
                "content": "We offer three tiers of service: Basic ($49/month), Professional ($99/month), and Enterprise (custom pricing). Each tier includes different feature sets and support levels to accommodate businesses of all sizes."
            },
            {
                "title": "Common Applications", 
                "content": "Our solution is commonly used for customer service management, data analytics, workflow optimization, and compliance tracking. It's particularly popular in retail, healthcare, finance, and technology sectors."
            },
            {
                "title": "Implementation Process", 
                "content": "Our standard implementation process takes 2-4 weeks and includes system integration, data migration, customization, and staff training. We provide dedicated support throughout the entire process."
            }
        ]
        
        # Filter results based on the query if needed
        # In a real implementation, this would use actual search logic
        return results