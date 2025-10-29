from __future__ import annotations

from typing import Annotated, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ScenarioVariable(BaseModel):
    """Describes a variable that authors can override at run time."""

    name: str
    description: str
    required: bool = False
    default: Optional[str] = None


class ScenarioEvidenceRequirement(BaseModel):
    """Evidence slots that can be bound to case documents during simulation."""

    id: str
    label: str
    description: Optional[str] = None
    required: bool = False
    document_id: Optional[str] = Field(default=None, description="Default document identifier")
    type: Literal["document", "timeline", "graph", "forensics"] = "document"


class ScenarioParticipant(BaseModel):
    """Participant metadata powering front-end rendering and voice selection."""

    id: str
    name: str
    role: str
    description: str
    sprite: HttpUrl | str
    accent_color: str = "#3b82f6"
    voice: Optional[str] = Field(default=None, description="Voice identifier understood by the TTS stack")
    default: bool = True
    optional: bool = False


class ScenarioBeatBase(BaseModel):
    """Common fields across scripted and dynamic beats."""

    id: str
    speaker: str
    stage_direction: Optional[str] = None
    emphasis: Optional[str] = Field(default=None, description="High-level emotional cue for rendering")
    duration_ms: Optional[int] = Field(default=None, ge=0)


class ScriptedBeat(ScenarioBeatBase):
    kind: Literal["scripted"] = "scripted"
    text: str


class DynamicBeat(ScenarioBeatBase):
    kind: Literal["dynamic"] = "dynamic"
    prompt_template: str = Field(
        description="Template rendered into a prompt for the orchestrator. Uses Python format syntax."
    )
    fallback_text: Optional[str] = Field(
        default=None,
        description="Optional fallback text used if orchestration fails",
    )
    delegate: Optional[str] = Field(
        default=None,
        description="Hint for downstream tooling about which agent persona should respond",
    )
    top_k: Optional[int] = Field(default=None, ge=1, le=20)


ScenarioBeat = Annotated[ScriptedBeat | DynamicBeat, Field(discriminator="kind")]


class ScenarioDefinition(BaseModel):
    """Canonical representation of a simulation scenario."""

    schema_version: Literal["1.0"] = "1.0"
    id: str
    title: str
    description: str
    category: Literal["hearing", "trial", "deposition", "custom"] = "trial"
    difficulty: Literal["intro", "associate", "expert"] = "associate"
    tags: List[str] = Field(default_factory=list)
    participants: List[ScenarioParticipant]
    variables: Dict[str, ScenarioVariable] = Field(default_factory=dict)
    evidence: List[ScenarioEvidenceRequirement] = Field(default_factory=list)
    beats: List[ScenarioBeat]

    @field_validator("participants")
    @classmethod
    def _ensure_unique_participants(cls, value: List[ScenarioParticipant]) -> List[ScenarioParticipant]:
        seen: set[str] = set()
        for participant in value:
            if participant.id in seen:
                raise ValueError(f"Duplicate participant id detected: {participant.id}")
            seen.add(participant.id)
        return value

    @field_validator("beats")
    @classmethod
    def _ensure_valid_speakers(cls, beats: List[ScenarioBeat], info) -> List[ScenarioBeat]:  # type: ignore[override]
        participants: Dict[str, ScenarioParticipant] = {p.id: p for p in info.data.get("participants", [])}
        for beat in beats:
            if beat.speaker not in participants:
                raise ValueError(f"Beat {beat.id} references unknown speaker {beat.speaker}")
        return beats


class ScenarioMetadata(BaseModel):
    """Lightweight projection for list endpoints."""

    id: str
    title: str
    description: str
    category: str
    difficulty: str
    tags: List[str]
    participants: List[str]


class ScenarioRunContext(BaseModel):
    """Context provided when running a scenario."""

    scenario_id: str
    case_id: str
    actor: Dict[str, object]
    variables: Dict[str, str]
    evidence: Dict[str, str]
    participants: List[str]
    tts_enabled: bool = False
