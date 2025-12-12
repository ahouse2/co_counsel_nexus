from typing import List, Dict, Any

def categorize_document(text: str, llm_service: Any) -> List[str]:
    """
    Categorizes a document based on its content using an LLM service.
    Args:
        text: The full text content of the document.
        llm_service: An LLM service capable of text classification.
    Returns:
        A list of categories assigned to the document.
    """
    # This is a placeholder for actual LLM interaction
    # In a real implementation, this would involve a call to an LLM API
    # with a carefully crafted prompt for categorization.
    prompt = f"Categorize the following legal document. Provide a comma-separated list of categories (e.g., 'Divorce, Child Custody, Financial Dispute'):\n\n{text[:2000]}..." # Truncate for prompt
    response = llm_service.generate_text(prompt) # Assuming llm_service has a generate_text method
    categories = [cat.strip() for cat in response.split(',') if cat.strip()]
    return categories

def tag_document(text: str, llm_service: Any) -> List[str]:
    """
    Generates relevant tags for a document based on its content using an LLM service.
    Args:
        text: The full text content of the document.
        llm_service: An LLM service capable of extracting keywords/tags.
    Returns:
        A list of tags assigned to the document.
    """
    # This is a placeholder for actual LLM interaction
    prompt = f"Extract key tags or keywords from the following legal document. Provide a comma-separated list of tags:\n\n{text[:2000]}..." # Truncate for prompt
    response = llm_service.generate_text(prompt)
    tags = [tag.strip() for tag in response.split(',') if tag.strip()]
    return tags

def heuristic_categorize(text: str) -> List[str]:
    """
    Categorizes a document based on keywords/regex without using an LLM.
    """
    text_lower = text.lower()
    categories = []
    
    # Define heuristics
    heuristics = {
        "Contract": ["agreement", "contract", "memorandum of understanding", "settlement agreement", "lease", "nda"],
        "Pleading": ["complaint", "answer", "motion", "petition", "affidavit", "declaration", "plaintiff", "defendant"],
        "Correspondence": ["email", "letter", "memorandum", "from:", "to:", "subject:"],
        "Financial": ["invoice", "receipt", "balance sheet", "tax return", "ledger", "financial statement", "profit and loss"],
        "Court Order": ["order", "judgment", "decree", "ruling", "opinion"],
        "Discovery": ["interrogatories", "request for production", "deposition", "subpoena"],
    }
    
    for category, keywords in heuristics.items():
        for keyword in keywords:
            if keyword in text_lower:
                categories.append(category)
                break # Found a match for this category, move to next
                
    return categories

def heuristic_tag(text: str) -> List[str]:
    """
    Generates tags based on keywords/regex without using an LLM.
    """
    text_lower = text.lower()
    tags = []
    
    # Simple keyword tagging
    keywords = ["confidential", "privileged", "draft", "final", "executed", "urgent", "internal"]
    
    for keyword in keywords:
        if keyword in text_lower:
            tags.append(keyword.title())
            
    return tags
