"""Static model catalog for supported AI providers.

This catalog enumerates the officially supported models for each provider that
is integrated with the Co-Counsel runtime.  The information is curated to match
public availability as of 2025-10-30 so that upstream services can surface
accurate defaults, validation, and capability negotiation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Tuple


class ProviderCapability(str, Enum):
    """Capabilities that a provider model can expose."""

    CHAT = "chat"
    EMBEDDINGS = "embeddings"
    VISION = "vision"


@dataclass(frozen=True)
class ModelInfo:
    """Metadata describing a supported model."""

    model_id: str
    display_name: str
    context_window: int
    modalities: Tuple[str, ...]
    capabilities: Tuple[ProviderCapability, ...]
    availability: str

    def supports(self, capability: ProviderCapability) -> bool:
        """Return True if the model supports the given capability."""

        return capability in self.capabilities


MODEL_CATALOG: Mapping[str, Tuple[ModelInfo, ...]] = {
    "openai": (
        ModelInfo(
            model_id="gpt-4.1",
            display_name="GPT-4.1",
            context_window=128_000,
            modalities=("text", "vision", "audio"),
            capabilities=(
                ProviderCapability.CHAT,
                ProviderCapability.VISION,
            ),
            availability="general-cloud",
        ),
        ModelInfo(
            model_id="gpt-4o",
            display_name="GPT-4o",
            context_window=128_000,
            modalities=("text", "vision", "audio"),
            capabilities=(
                ProviderCapability.CHAT,
                ProviderCapability.VISION,
            ),
            availability="general-cloud",
        ),
        ModelInfo(
            model_id="gpt-4o-mini",
            display_name="GPT-4o Mini",
            context_window=65_536,
            modalities=("text", "vision"),
            capabilities=(
                ProviderCapability.CHAT,
                ProviderCapability.VISION,
            ),
            availability="general-cloud",
        ),
        ModelInfo(
            model_id="o4-mini-high",
            display_name="o4 Mini High",
            context_window=32_768,
            modalities=("text",),
            capabilities=(ProviderCapability.CHAT,),
            availability="limited-cloud",
        ),
        ModelInfo(
            model_id="text-embedding-3-large",
            display_name="Text Embedding 3 Large",
            context_window=8_192,
            modalities=("text",),
            capabilities=(ProviderCapability.EMBEDDINGS,),
            availability="general-cloud",
        ),
        ModelInfo(
            model_id="text-embedding-3-small",
            display_name="Text Embedding 3 Small",
            context_window=8_192,
            modalities=("text",),
            capabilities=(ProviderCapability.EMBEDDINGS,),
            availability="general-cloud",
        ),
    ),
    "azure-openai": (
        ModelInfo(
            model_id="gpt-4.1",
            display_name="GPT-4.1 (Azure)",
            context_window=128_000,
            modalities=("text", "vision", "audio"),
            capabilities=(
                ProviderCapability.CHAT,
                ProviderCapability.VISION,
            ),
            availability="azure-managed",
        ),
        ModelInfo(
            model_id="gpt-4o",
            display_name="GPT-4o (Azure)",
            context_window=128_000,
            modalities=("text", "vision", "audio"),
            capabilities=(
                ProviderCapability.CHAT,
                ProviderCapability.VISION,
            ),
            availability="azure-managed",
        ),
        ModelInfo(
            model_id="gpt-4o-mini",
            display_name="GPT-4o Mini (Azure)",
            context_window=65_536,
            modalities=("text", "vision"),
            capabilities=(
                ProviderCapability.CHAT,
                ProviderCapability.VISION,
            ),
            availability="azure-managed",
        ),
        ModelInfo(
            model_id="text-embedding-3-large",
            display_name="Text Embedding 3 Large (Azure)",
            context_window=8_192,
            modalities=("text",),
            capabilities=(ProviderCapability.EMBEDDINGS,),
            availability="azure-managed",
        ),
        ModelInfo(
            model_id="text-embedding-3-small",
            display_name="Text Embedding 3 Small (Azure)",
            context_window=8_192,
            modalities=("text",),
            capabilities=(ProviderCapability.EMBEDDINGS,),
            availability="azure-managed",
        ),
    ),
    "gemini": (
        ModelInfo(
            model_id="gemini-2.0-pro-exp",
            display_name="Gemini 2.0 Pro Experimental",
            context_window=2_000_000,
            modalities=("text", "vision", "audio"),
            capabilities=(
                ProviderCapability.CHAT,
                ProviderCapability.VISION,
            ),
            availability="general-cloud",
        ),
        ModelInfo(
            model_id="gemini-1.5-pro",
            display_name="Gemini 1.5 Pro",
            context_window=2_000_000,
            modalities=("text", "vision", "audio"),
            capabilities=(
                ProviderCapability.CHAT,
                ProviderCapability.VISION,
            ),
            availability="general-cloud",
        ),
        ModelInfo(
            model_id="gemini-1.5-flash",
            display_name="Gemini 1.5 Flash",
            context_window=1_000_000,
            modalities=("text", "vision"),
            capabilities=(
                ProviderCapability.CHAT,
                ProviderCapability.VISION,
            ),
            availability="general-cloud",
        ),
        ModelInfo(
            model_id="gemini-1.5-flash-8b",
            display_name="Gemini 1.5 Flash 8B",
            context_window=1_000_000,
            modalities=("text", "vision"),
            capabilities=(
                ProviderCapability.CHAT,
                ProviderCapability.VISION,
            ),
            availability="general-cloud",
        ),
        ModelInfo(
            model_id="text-embedding-004",
            display_name="Text Embedding 004",
            context_window=8_192,
            modalities=("text",),
            capabilities=(ProviderCapability.EMBEDDINGS,),
            availability="general-cloud",
        ),
    ),
    "huggingface": (
        ModelInfo(
            model_id="mistral-large-2411",
            display_name="Mistral Large 24.11",
            context_window=128_000,
            modalities=("text",),
            capabilities=(ProviderCapability.CHAT,),
            availability="hosted-api",
        ),
        ModelInfo(
            model_id="mixtral-8x22b-instruct",
            display_name="Mixtral 8x22B Instruct",
            context_window=65_536,
            modalities=("text",),
            capabilities=(ProviderCapability.CHAT,),
            availability="hosted-api",
        ),
        ModelInfo(
            model_id="phi-4",
            display_name="Phi-4",
            context_window=32_768,
            modalities=("text", "vision"),
            capabilities=(
                ProviderCapability.CHAT,
                ProviderCapability.VISION,
            ),
            availability="hosted-api",
        ),
        ModelInfo(
            model_id="nomic-embed-text-v1.5",
            display_name="Nomic Embed Text v1.5",
            context_window=8_192,
            modalities=("text",),
            capabilities=(ProviderCapability.EMBEDDINGS,),
            availability="hosted-api",
        ),
    ),
    "ollama": (
        ModelInfo(
            model_id="llama3.1",
            display_name="Llama 3.1 8B",
            context_window=128_000,
            modalities=("text",),
            capabilities=(ProviderCapability.CHAT,),
            availability="local-runtime",
        ),
        ModelInfo(
            model_id="llama3.2-vision",
            display_name="Llama 3.2 Vision",
            context_window=80_000,
            modalities=("text", "vision"),
            capabilities=(
                ProviderCapability.CHAT,
                ProviderCapability.VISION,
            ),
            availability="local-runtime",
        ),
        ModelInfo(
            model_id="phi4",
            display_name="Phi-4",
            context_window=32_768,
            modalities=("text",),
            capabilities=(ProviderCapability.CHAT,),
            availability="local-runtime",
        ),
        ModelInfo(
            model_id="nomic-embed-text",
            display_name="Nomic Embed Text",
            context_window=8_192,
            modalities=("text",),
            capabilities=(ProviderCapability.EMBEDDINGS,),
            availability="local-runtime",
        ),
    ),
    "llama.cpp": (
        ModelInfo(
            model_id="llama-3.1-8b-instruct-q4",
            display_name="Llama 3.1 8B Instruct Q4",
            context_window=128_000,
            modalities=("text",),
            capabilities=(ProviderCapability.CHAT,),
            availability="local-runtime",
        ),
        ModelInfo(
            model_id="llama-3.1-70b-instruct-q4",
            display_name="Llama 3.1 70B Instruct Q4",
            context_window=128_000,
            modalities=("text",),
            capabilities=(ProviderCapability.CHAT,),
            availability="local-runtime",
        ),
        ModelInfo(
            model_id="phi-3-medium-4k-instruct-q4",
            display_name="Phi-3 Medium 4K Instruct Q4",
            context_window=4_096,
            modalities=("text",),
            capabilities=(ProviderCapability.CHAT,),
            availability="local-runtime",
        ),
        ModelInfo(
            model_id="mistral-nemo-instruct-q4",
            display_name="Mistral Nemo Instruct Q4",
            context_window=32_768,
            modalities=("text",),
            capabilities=(ProviderCapability.CHAT,),
            availability="local-runtime",
        ),
        ModelInfo(
            model_id="all-minilm-l6-v2-gguf",
            display_name="all-MiniLM-L6-v2 GGUF",
            context_window=4_096,
            modalities=("text",),
            capabilities=(ProviderCapability.EMBEDDINGS,),
            availability="local-runtime",
        ),
    ),
    "gguf-local": (
        ModelInfo(
            model_id="llama-3.2-vision-q4",
            display_name="Llama 3.2 Vision Q4 GGUF",
            context_window=80_000,
            modalities=("text", "vision"),
            capabilities=(
                ProviderCapability.CHAT,
                ProviderCapability.VISION,
            ),
            availability="local-runtime",
        ),
        ModelInfo(
            model_id="phi-3.5-mini-instruct-q4",
            display_name="Phi-3.5 Mini Instruct Q4 GGUF",
            context_window=16_384,
            modalities=("text",),
            capabilities=(ProviderCapability.CHAT,),
            availability="local-runtime",
        ),
        ModelInfo(
            model_id="mistral-small-instruct-q4",
            display_name="Mistral Small Instruct Q4 GGUF",
            context_window=32_768,
            modalities=("text",),
            capabilities=(ProviderCapability.CHAT,),
            availability="local-runtime",
        ),
        ModelInfo(
            model_id="gte-small-gguf",
            display_name="GTE Small GGUF",
            context_window=8_192,
            modalities=("text",),
            capabilities=(ProviderCapability.EMBEDDINGS,),
            availability="local-runtime",
        ),
    ),
}


__all__ = ["ModelInfo", "MODEL_CATALOG", "ProviderCapability"]
