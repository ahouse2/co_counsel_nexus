from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

import yaml


@dataclass(frozen=True)
class PromptMessage:
    role: str
    template: str

    def render(self, variables: Mapping[str, Any]) -> Dict[str, str]:
        try:
            content = self.template.format(**variables)
        except KeyError as exc:  # pragma: no cover - converted by caller
            missing = exc.args[0]
            raise ValueError(f"Missing variable '{missing}' for prompt message ({self.role})") from exc
        return {"role": self.role, "content": content}


@dataclass
class PromptTemplate:
    template_id: str
    description: str
    variables: List[str]
    messages: List[PromptMessage]
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"

    def render(self, **variables: Any) -> List[Dict[str, str]]:
        missing = set(self.variables) - set(variables.keys())
        if missing:
            missing_values = ", ".join(sorted(missing))
            raise ValueError(f"Missing variables for template '{self.template_id}': {missing_values}")
        payload = {name: variables[name] for name in self.variables}
        return [message.render(payload) for message in self.messages]

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "PromptTemplate":
        template_id = str(payload["id"]).strip()
        description = str(payload.get("description", "")).strip()
        variables = [str(item) for item in payload.get("inputs", [])]
        messages = [
            PromptMessage(role=str(item["role"]).strip(), template=str(item["template"]))
            for item in payload.get("messages", [])
        ]
        metadata = dict(payload.get("metadata", {}))
        version = str(payload.get("version", "1.0.0"))
        if not template_id:
            raise ValueError("Prompt template identifier may not be blank")
        if not messages:
            raise ValueError(f"Prompt template '{template_id}' has no messages")
        return cls(
            template_id=template_id,
            description=description,
            variables=variables,
            messages=messages,
            metadata=metadata,
            version=version,
        )


@dataclass
class PromptPack:
    name: str
    agent_type: str
    version: str
    description: str
    templates: Dict[str, PromptTemplate]
    metadata: Dict[str, Any]
    checksum: str
    source_path: Path

    def template(self, template_id: str) -> PromptTemplate:
        try:
            return self.templates[template_id]
        except KeyError as exc:
            raise KeyError(f"Prompt template '{template_id}' not found in pack '{self.name}'") from exc

    def render(self, template_id: str, **variables: Any) -> List[Dict[str, str]]:
        return self.template(template_id).render(**variables)

    def list_templates(self) -> Iterable[str]:
        return self.templates.keys()

    @classmethod
    def load(cls, path: str | Path) -> "PromptPack":
        pack_path = Path(path)
        data = yaml.safe_load(pack_path.read_text())
        if not isinstance(data, dict):
            raise ValueError(f"Prompt pack at {pack_path} is not a mapping")
        meta = data.get("meta") or {}
        prompts = data.get("prompts") or []
        if not prompts:
            raise ValueError(f"Prompt pack at {pack_path} does not define any prompts")
        name = str(meta.get("name") or pack_path.stem)
        agent_type = str(meta.get("agent_type") or "general")
        version = str(meta.get("version", "1.0.0"))
        description = str(meta.get("description", ""))
        templates: Dict[str, PromptTemplate] = {}
        for entry in prompts:
            template = PromptTemplate.from_dict(entry)
            if template.template_id in templates:
                raise ValueError(f"Duplicate prompt template '{template.template_id}' in pack {name}")
            templates[template.template_id] = template
        checksum = hashlib.sha256(
            json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        metadata = {
            key: value
            for key, value in meta.items()
            if key not in {"name", "version", "agent_type", "description"}
        }
        return cls(
            name=name,
            agent_type=agent_type,
            version=version,
            description=description,
            templates=templates,
            metadata=metadata,
            checksum=checksum,
            source_path=pack_path.resolve(),
        )


__all__ = [
    "PromptPack",
    "PromptTemplate",
    "PromptMessage",
]
