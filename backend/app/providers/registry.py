"""Provider registry and adapter definitions."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Mapping, MutableMapping, Sequence

from .catalog import MODEL_CATALOG, ModelInfo, ProviderCapability


class ProviderRegistryError(RuntimeError):
    """Base error for provider registry failures."""


class ProviderNotFoundError(ProviderRegistryError):
    """Raised when the registry does not contain a requested provider."""


class ProviderCapabilityError(ProviderRegistryError):
    """Raised when a provider cannot satisfy the desired capability."""


@dataclass(frozen=True)
class ProviderDescriptor:
    """Describes a configured provider instance."""

    provider_id: str
    display_name: str
    base_url: str | None
    runtime_path: Path | None


class ChatProvider:
    """Interface for chat capable providers."""

    def list_chat_models(self) -> Sequence[ModelInfo]:  # pragma: no cover - Protocol-like
        raise NotImplementedError

    def default_chat_model(self) -> ModelInfo:  # pragma: no cover - Protocol-like
        raise NotImplementedError


class EmbeddingProvider:
    """Interface for embedding capable providers."""

    def list_embedding_models(self) -> Sequence[ModelInfo]:  # pragma: no cover
        raise NotImplementedError

    def default_embedding_model(self) -> ModelInfo:  # pragma: no cover
        raise NotImplementedError


class VisionProvider:
    """Interface for vision capable providers."""

    def list_vision_models(self) -> Sequence[ModelInfo]:  # pragma: no cover
        raise NotImplementedError

    def default_vision_model(self) -> ModelInfo:  # pragma: no cover
        raise NotImplementedError


class BaseProviderAdapter(ChatProvider, EmbeddingProvider, VisionProvider):
    """Base adapter for provider metadata sourced from the catalog."""

    provider_id: str = ""
    display_name: str = ""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        runtime_path: Path | None = None,
    ) -> None:
        models = MODEL_CATALOG.get(self.provider_id)
        if not models:
            raise ProviderNotFoundError(
                f"No catalog entries registered for provider '{self.provider_id}'."
            )
        self._models: tuple[ModelInfo, ...] = models
        self._base_url = base_url
        self._runtime_path = runtime_path

    @property
    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=self.provider_id,
            display_name=self.display_name,
            base_url=self._base_url,
            runtime_path=self._runtime_path,
        )

    def list_models(
        self, capability: ProviderCapability | None = None
    ) -> Sequence[ModelInfo]:
        if capability is None:
            return self._models
        return tuple(model for model in self._models if model.supports(capability))

    def _ensure_capability(self, capability: ProviderCapability) -> Sequence[ModelInfo]:
        models = self.list_models(capability)
        if not models:
            raise ProviderCapabilityError(
                f"Provider '{self.provider_id}' does not support capability '{capability.value}'."
            )
        return models

    def list_chat_models(self) -> Sequence[ModelInfo]:
        return self._ensure_capability(ProviderCapability.CHAT)

    def list_embedding_models(self) -> Sequence[ModelInfo]:
        return self._ensure_capability(ProviderCapability.EMBEDDINGS)

    def list_vision_models(self) -> Sequence[ModelInfo]:
        return self._ensure_capability(ProviderCapability.VISION)

    def _default_model(self, capability: ProviderCapability) -> ModelInfo:
        models = self._ensure_capability(capability)
        return models[0]

    def default_chat_model(self) -> ModelInfo:
        return self._default_model(ProviderCapability.CHAT)

    def default_embedding_model(self) -> ModelInfo:
        return self._default_model(ProviderCapability.EMBEDDINGS)

    def default_vision_model(self) -> ModelInfo:
        return self._default_model(ProviderCapability.VISION)


class GeminiProviderAdapter(BaseProviderAdapter):
    provider_id = "gemini"
    display_name = "Google Gemini"


class OpenAIProviderAdapter(BaseProviderAdapter):
    provider_id = "openai"
    display_name = "OpenAI"


class AzureOpenAIProviderAdapter(BaseProviderAdapter):
    provider_id = "azure-openai"
    display_name = "Azure OpenAI"


class HuggingFaceProviderAdapter(BaseProviderAdapter):
    provider_id = "huggingface"
    display_name = "Hugging Face Inference"


class OllamaProviderAdapter(BaseProviderAdapter):
    provider_id = "ollama"
    display_name = "Ollama"


class LlamaCppProviderAdapter(BaseProviderAdapter):
    provider_id = "llama.cpp"
    display_name = "llama.cpp"


class GGUFLocalProviderAdapter(BaseProviderAdapter):
    provider_id = "gguf-local"
    display_name = "Local GGUF Runner"


ADAPTER_TYPES: Mapping[str, type[BaseProviderAdapter]] = {
    adapter.provider_id: adapter
    for adapter in (
        GeminiProviderAdapter,
        OpenAIProviderAdapter,
        AzureOpenAIProviderAdapter,
        HuggingFaceProviderAdapter,
        OllamaProviderAdapter,
        LlamaCppProviderAdapter,
        GGUFLocalProviderAdapter,
    )
}


@dataclass
class ProviderResolution:
    """Represents the result of resolving a provider for a capability."""

    provider: BaseProviderAdapter
    model: ModelInfo


class ProviderRegistry:
    """Registry that coordinates provider selection and defaults."""

    def __init__(
        self,
        *,
        primary_provider: str,
        secondary_provider: str | None,
        api_base_urls: Mapping[str, str],
        runtime_paths: Mapping[str, Path],
        model_overrides: Mapping[ProviderCapability, str | None] | None = None,
    ) -> None:
        self._primary_provider = primary_provider
        self._secondary_provider = secondary_provider
        self._api_base_urls = dict(api_base_urls)
        self._runtime_paths = dict(runtime_paths)
        self._model_overrides = dict(model_overrides or {})
        self._adapters: MutableMapping[str, BaseProviderAdapter] = {}

    def _build_adapter(self, provider_id: str) -> BaseProviderAdapter:
        adapter_type = ADAPTER_TYPES.get(provider_id)
        if not adapter_type:
            raise ProviderNotFoundError(f"Provider '{provider_id}' is not registered.")

        base_url = self._api_base_urls.get(provider_id)
        runtime_path = self._runtime_paths.get(provider_id)
        return adapter_type(base_url=base_url, runtime_path=runtime_path)

    def get_adapter(self, provider_id: str) -> BaseProviderAdapter:
        if provider_id not in self._adapters:
            self._adapters[provider_id] = self._build_adapter(provider_id)
        return self._adapters[provider_id]

    def list_providers(self) -> Sequence[str]:
        return tuple(ADAPTER_TYPES.keys())

    def _resolve_provider_chain(self, capability: ProviderCapability) -> Sequence[str]:
        ordered = []
        if self._primary_provider:
            ordered.append(self._primary_provider)
        if self._secondary_provider and self._secondary_provider not in ordered:
            ordered.append(self._secondary_provider)
        # add remaining providers that support capability
        for provider_id in ADAPTER_TYPES:
            if provider_id in ordered:
                continue
            try:
                adapter = self.get_adapter(provider_id)
                adapter.list_models(capability)
                ordered.append(provider_id)
            except ProviderCapabilityError:
                continue
        return tuple(ordered)

    def _resolve_model_override(self, capability: ProviderCapability) -> str | None:
        override = self._model_overrides.get(capability)
        return override

    def resolve(self, capability: ProviderCapability) -> ProviderResolution:
        """Resolve a provider/model pair for the requested capability."""

        model_override = self._resolve_model_override(capability)
        errors: Dict[str, Exception] = {}
        candidates: list[tuple[BaseProviderAdapter, Sequence[ModelInfo]]] = []
        for provider_id in self._resolve_provider_chain(capability):
            try:
                adapter = self.get_adapter(provider_id)
                models = adapter.list_models(capability)
            except ProviderCapabilityError as exc:
                errors[provider_id] = exc
                continue
            candidates.append((adapter, models))

        if not candidates:
            if errors:
                raise ProviderCapabilityError(
                    f"No providers could satisfy capability '{capability.value}': "
                    + ", ".join(sorted(errors))
                )
            raise ProviderCapabilityError(
                f"Capability '{capability.value}' is not supported by any provider."
            )

        if model_override:
            for adapter, models in candidates:
                for model in models:
                    if model.model_id == model_override:
                        return ProviderResolution(provider=adapter, model=model)

        adapter, models = candidates[0]
        return ProviderResolution(provider=adapter, model=models[0])


@lru_cache(maxsize=1)
def get_provider_registry(
    *,
    primary_provider: str,
    secondary_provider: str | None,
    api_base_urls: Mapping[str, str],
    runtime_paths: Mapping[str, Path],
    model_overrides: Mapping[ProviderCapability, str | None] | None = None,
) -> ProviderRegistry:
    """Return a cached provider registry."""

    return ProviderRegistry(
        primary_provider=primary_provider,
        secondary_provider=secondary_provider,
        api_base_urls=api_base_urls,
        runtime_paths=runtime_paths,
        model_overrides=model_overrides,
    )


def reset_provider_registry_cache() -> None:
    """Clear the cached provider registry factory."""

    get_provider_registry.cache_clear()


__all__ = [
    "ProviderRegistry",
    "ProviderDescriptor",
    "ProviderCapability",
    "ProviderResolution",
    "ProviderNotFoundError",
    "ProviderCapabilityError",
    "get_provider_registry",
    "reset_provider_registry_cache",
]
