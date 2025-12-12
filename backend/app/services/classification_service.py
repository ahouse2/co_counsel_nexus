import logging
from typing import List, Dict, Any
from pydantic import BaseModel, Field

from llama_index.core.selectors import LLMMultiSelector, SelectorResult
from llama_index.core.schema import TextNode
from llama_index.core.tools import ToolMetadata

from backend.app.services.llm_service import BaseLlmService
from backend.ingestion.llama_index_factory import create_llm_service
from backend.app.config import get_settings

logger = logging.getLogger(__name__)

class ClassificationResult(BaseModel):
    categories: List[str]
    scores: List[float]
    reasoning: str

class ClassificationService:
    """
    Service for classifying documents using LlamaIndex's LLMMultiSelector.
    """
    def __init__(self, llm_service: BaseLlmService = None):
        settings = get_settings()
        # We need the underlying LlamaIndex LLM, but our factory returns a wrapper.
        # However, LLMMultiSelector expects a LlamaIndex LLM.
        # We'll use the factory to get the config and instantiate the LlamaIndex LLM directly 
        # or adapt our wrapper if possible. 
        # For now, let's re-use the logic from `create_extractors` in `llama_index_factory` 
        # to get a proper LlamaIndex LLM instance.
        
        self.llm = self._get_llama_index_llm(settings.llm)
        
        # Define our categories as "Tools" for the selector
        # This is how LlamaIndex selectors work - they select from a list of choices.
        self.choices = [
            ToolMetadata(description="Legal agreement, contract, lease, or NDA.", name="Contract"),
            ToolMetadata(description="Formal court filing like complaint, answer, motion, or petition.", name="Pleading"),
            ToolMetadata(description="Communication between parties, emails, letters, or memos.", name="Correspondence"),
            ToolMetadata(description="Financial record, invoice, receipt, tax return, or ledger.", name="Financial"),
            ToolMetadata(description="Official court order, judgment, decree, or ruling.", name="Court Order"),
            ToolMetadata(description="Discovery document, interrogatory, deposition, or subpoena.", name="Discovery"),
            ToolMetadata(description="Evidence, photos, videos, or physical exhibits.", name="Evidence"),
            ToolMetadata(description="Other legal document not fitting the above categories.", name="Other"),
        ]
        
        self.selector = LLMMultiSelector.from_defaults(llm=self.llm)

    def _get_llama_index_llm(self, config):
        """
        Helper to instantiate LlamaIndex LLM based on config.
        Duplicated logic from llama_index_factory for now to avoid circular imports or complex refactors.
        """
        from backend.app.models.settings import LlmProvider
        try:
            if config.provider == LlmProvider.OPENAI:
                from llama_index.llms.openai import OpenAI
                return OpenAI(model=config.model, api_key=config.api_key, api_base=config.api_base)
            elif config.provider == LlmProvider.AZURE_OPENAI:
                from llama_index.llms.azure_openai import AzureOpenAI
                return AzureOpenAI(
                    model=config.model,
                    deployment_name=config.extra.get("azure_deployment"),
                    api_key=config.api_key,
                    azure_endpoint=config.api_base,
                    api_version=config.extra.get("api_version"),
                )
            elif config.provider == LlmProvider.GEMINI:
                from llama_index.llms.gemini import Gemini
                return Gemini(model=config.model, api_key=config.api_key)
            elif config.provider == LlmProvider.OLLAMA:
                from llama_index.llms.ollama import Ollama
                return Ollama(model=config.model, base_url=config.api_base)
        except ImportError:
            logger.warning("Could not import LlamaIndex LLM provider. Classification may fail.")
        return None

    def classify_document_sync(self, text: str) -> ClassificationResult:
        """
        Synchronous version of classify_document.
        """
        if not self.llm:
            logger.warning("No LLM available for classification. Returning empty.")
            return ClassificationResult(categories=[], scores=[], reasoning="No LLM configured.")

        truncated_text = text[:3000] 
        
        try:
            # Use sync select
            result: SelectorResult = self.selector.select(
                self.choices, 
                query=f"Classify this document based on its content: {truncated_text}"
            )
            
            categories = []
            scores = []
            reasoning = "LlamaIndex Classification"
            
            for selection in result.selections:
                choice = self.choices[selection.index]
                categories.append(choice.name)
                scores.append(selection.score if hasattr(selection, 'score') else 1.0)
                if hasattr(selection, 'reason'):
                     reasoning = selection.reason
            
            return ClassificationResult(
                categories=categories,
                scores=scores,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Classification failed: {e}", exc_info=True)
            return ClassificationResult(categories=[], scores=[], reasoning=f"Error: {str(e)}")

    async def classify_document(self, text: str) -> ClassificationResult:
        """
        Classifies the document text into predefined categories.
        """
        if not self.llm:
            logger.warning("No LLM available for classification. Returning empty.")
            return ClassificationResult(categories=[], scores=[], reasoning="No LLM configured.")

        # Truncate text to avoid context window issues
        truncated_text = text[:3000] 
        
        try:
            # The selector expects a list of choices and a query (the text to classify)
            # We treat the text as the 'query' to match against choices.
            result: SelectorResult = await self.selector.aselect(
                self.choices, 
                query=f"Classify this document based on its content: {truncated_text}"
            )
            
            categories = []
            scores = []
            reasoning = "LlamaIndex Classification"
            
            for selection in result.selections:
                # selection.index is the index in self.choices
                # selection.reason is the reasoning
                choice = self.choices[selection.index]
                categories.append(choice.name)
                scores.append(selection.score if hasattr(selection, 'score') else 1.0) # LLMMultiSelector might not return score in all versions
                if hasattr(selection, 'reason'):
                     reasoning = selection.reason
            
            return ClassificationResult(
                categories=categories,
                scores=scores,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Classification failed: {e}", exc_info=True)
            return ClassificationResult(categories=[], scores=[], reasoning=f"Error: {str(e)}")
