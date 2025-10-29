from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from uuid import uuid4

from ..config import get_settings
from ..scenarios import ScenarioDefinition, ScenarioRegistry, ScenarioRegistryError
from ..scenarios.schema import DynamicBeat, ScenarioParticipant, ScriptedBeat
from ..security.authz import Principal
from ..storage.agent_memory_store import AgentMemoryStore, ScenarioRunRecord
from .agents import AgentsService, get_agents_service
from .errors import WorkflowAbort, WorkflowComponent, WorkflowError, WorkflowException
from .tts import TextToSpeechResult, TextToSpeechService, get_tts_service


@dataclass(slots=True)
class ScenarioEvidenceBinding:
    slot_id: str
    value: str
    document_id: Optional[str] = None
    type: Optional[str] = None


@dataclass(slots=True)
class ScenarioRunOptions:
    scenario_id: str
    case_id: str
    variables: Dict[str, str]
    evidence: Dict[str, ScenarioEvidenceBinding]
    participants: List[str]
    use_tts: bool = False


@dataclass(slots=True)
class ScenarioTurnResult:
    beat_id: str
    speaker: ScenarioParticipant
    text: str
    kind: str
    stage_direction: Optional[str]
    emphasis: Optional[str]
    duration_ms: Optional[float]
    dynamic_source_thread: Optional[str]
    telemetry: Dict[str, object]
    audio: Optional[TextToSpeechResult]


class ScenarioEngine:
    """Executes scripted simulation scenarios with dynamic agent prompts."""

    def __init__(
        self,
        *,
        registry: ScenarioRegistry | None = None,
        agents_service: AgentsService | None = None,
        tts_service: TextToSpeechService | None = None,
        memory_store: AgentMemoryStore | None = None,
    ) -> None:
        self.settings = get_settings()
        default_library = (
            Path(__file__).resolve().parent.parent / "scenarios" / "library"
        )
        library_path = getattr(self.settings, "scenario_library_path", None)
        self.registry = registry or ScenarioRegistry(library_path or default_library)
        self.agents = agents_service or get_agents_service()
        self.tts = tts_service or get_tts_service(optional=True)
        self.memory = memory_store or self.agents.memory_store
        self.default_top_k = max(1, getattr(self.settings, "scenario_default_top_k", 4))

    def list(self) -> List[ScenarioDefinition]:
        return [self.registry.get(meta.id) for meta in self.registry.list()]

    def list_metadata(self):
        return self.registry.list()

    def get(self, scenario_id: str) -> ScenarioDefinition:
        try:
            return self.registry.get(scenario_id)
        except ScenarioRegistryError as exc:
            raise WorkflowAbort(
                WorkflowError(
                    component=WorkflowComponent.SCENARIO,
                    code="SCENARIO_NOT_FOUND",
                    message=str(exc),
                ),
                status_code=404,
            ) from exc

    def run(
        self,
        options: ScenarioRunOptions,
        *,
        principal: Principal | None = None,
    ) -> Dict[str, object]:
        scenario = self.get(options.scenario_id)
        participants = self._resolve_participants(scenario, options.participants)
        context = self._build_context(scenario, participants, options)
        run_id = str(uuid4())
        transcript: List[Dict[str, object]] = []
        telemetry: Dict[str, object] = {
            "beats": [],
            "dynamic_threads": [],
            "tts": {"synthesised": 0},
        }
        for beat in scenario.beats:
            started = time.perf_counter()
            if isinstance(beat, ScriptedBeat):
                result = self._handle_scripted(beat, participants[beat.speaker], options.use_tts)
            else:
                result = self._handle_dynamic(
                    scenario,
                    beat,
                    participants[beat.speaker],
                    context,
                    options,
                    principal=principal,
                    telemetry=telemetry,
                )
            elapsed = (time.perf_counter() - started) * 1000.0
            telemetry.setdefault("beats", []).append(
                {
                    "beat_id": beat.id,
                    "kind": result.kind,
                    "speaker": result.speaker.id,
                    "duration_ms": round(elapsed, 2),
                    "thread_id": result.dynamic_source_thread,
                }
            )
            turn_payload = {
                "beat_id": result.beat_id,
                "speaker_id": result.speaker.id,
                "speaker": {
                    "id": result.speaker.id,
                    "name": result.speaker.name,
                    "role": result.speaker.role,
                    "voice": result.speaker.voice,
                    "accent_color": result.speaker.accent_color,
                    "sprite": result.speaker.sprite,
                },
                "text": result.text,
                "kind": result.kind,
                "stage_direction": result.stage_direction,
                "emphasis": result.emphasis,
                "duration_ms": result.duration_ms,
                "thread_id": result.dynamic_source_thread,
            }
            if result.audio is not None:
                telemetry["tts"]["synthesised"] += 1
                turn_payload["audio"] = {
                    "voice": result.audio.voice,
                    "mime_type": result.audio.content_type,
                    "base64": base64.b64encode(result.audio.audio_bytes).decode("ascii"),
                    "cache_hit": result.audio.cache_hit,
                    "sha256": result.audio.sha256,
                }
            transcript.append(turn_payload)
            context[f"beat_{beat.id}_text"] = result.text
            context[f"{result.speaker.id}_last_line"] = result.text
        actor = self._actor_from_principal(principal)
        record = ScenarioRunRecord(
            run_id=run_id,
            scenario_id=scenario.id,
            case_id=options.case_id,
            created_at=datetime.now(timezone.utc),
            actor=actor,
            configuration={
                "variables": dict(options.variables),
                "evidence": {
                    slot: {
                        "value": binding.value,
                        "documentId": binding.document_id,
                        "type": binding.type,
                    }
                    for slot, binding in options.evidence.items()
                },
                "participants": [participant.id for participant in participants.values()],
                "tts": options.use_tts,
            },
            transcript=transcript,
            telemetry=telemetry,
        )
        self.memory.write_scenario(record)
        return {
            "run_id": run_id,
            "scenario": scenario.model_dump(mode="json"),
            "transcript": transcript,
            "telemetry": telemetry,
        }

    def _build_context(
        self,
        scenario: ScenarioDefinition,
        participants: Dict[str, ScenarioParticipant],
        options: ScenarioRunOptions,
    ) -> Dict[str, str]:
        context = dict(options.variables)
        for slot in scenario.evidence:
            binding = options.evidence.get(slot.id)
            if binding:
                context[slot.id] = binding.value
                if binding.document_id:
                    context[f"{slot.id}_document"] = binding.document_id
            elif slot.document_id:
                context[slot.id] = slot.document_id
            elif slot.required:
                raise WorkflowAbort(
                    WorkflowError(
                        component=WorkflowComponent.SCENARIO,
                        code="SCENARIO_EVIDENCE_MISSING",
                        message=f"Required evidence slot {slot.id} must be provided",
                    )
                )
        for participant in participants.values():
            context[f"{participant.id}_name"] = participant.name
            context[f"{participant.id}_role"] = participant.role
        return context

    def _resolve_participants(
        self,
        scenario: ScenarioDefinition,
        selected: Iterable[str],
    ) -> Dict[str, ScenarioParticipant]:
        available = {participant.id: participant for participant in scenario.participants}
        active: Dict[str, ScenarioParticipant] = {}
        selected_set = set(selected)
        for participant in scenario.participants:
            if participant.optional and participant.id not in selected_set:
                continue
            active[participant.id] = participant
        missing_required = [p.id for p in scenario.participants if not p.optional and p.id not in active]
        if missing_required:
            raise WorkflowAbort(
                WorkflowError(
                    component=WorkflowComponent.SCENARIO,
                    code="SCENARIO_PARTICIPANT_MISSING",
                    message=f"Missing required participants: {', '.join(sorted(missing_required))}",
                )
            )
        for participant_id in selected_set:
            if participant_id not in available:
                raise WorkflowAbort(
                    WorkflowError(
                        component=WorkflowComponent.SCENARIO,
                        code="SCENARIO_PARTICIPANT_UNKNOWN",
                        message=f"Participant {participant_id} is not defined in scenario {scenario.id}",
                    )
                )
            active[participant_id] = available[participant_id]
        return active

    def _handle_scripted(
        self,
        beat: ScriptedBeat,
        participant: ScenarioParticipant,
        use_tts: bool,
    ) -> ScenarioTurnResult:
        audio = self._maybe_synthesise(beat.text, participant, use_tts)
        return ScenarioTurnResult(
            beat_id=beat.id,
            speaker=participant,
            text=beat.text,
            kind=beat.kind,
            stage_direction=beat.stage_direction,
            emphasis=beat.emphasis,
            duration_ms=float(beat.duration_ms) if beat.duration_ms is not None else None,
            dynamic_source_thread=None,
            telemetry={},
            audio=audio,
        )

    def _handle_dynamic(
        self,
        scenario: ScenarioDefinition,
        beat: DynamicBeat,
        participant: ScenarioParticipant,
        context: Dict[str, str],
        options: ScenarioRunOptions,
        *,
        principal: Principal | None,
        telemetry: Dict[str, object],
    ) -> ScenarioTurnResult:
        try:
            prompt = beat.prompt_template.format(**context)
        except KeyError as exc:
            raise WorkflowAbort(
                WorkflowError(
                    component=WorkflowComponent.SCENARIO,
                    code="SCENARIO_PROMPT_RENDER_ERROR",
                    message=f"Missing variable {exc.args[0]} for beat {beat.id}",
                )
            ) from exc
        try:
            response = self.agents.run_case(
                options.case_id,
                prompt,
                top_k=beat.top_k or self.default_top_k,
                principal=principal,
            )
        except WorkflowException as exc:
            if beat.fallback_text:
                telemetry.setdefault("errors", []).append(exc.error.to_dict())
                audio = self._maybe_synthesise(beat.fallback_text, participant, options.use_tts)
                return ScenarioTurnResult(
                    beat_id=beat.id,
                    speaker=participant,
                    text=beat.fallback_text,
                    kind=beat.kind,
                    stage_direction=beat.stage_direction,
                    emphasis=beat.emphasis,
                    duration_ms=None,
                    dynamic_source_thread=None,
                    telemetry={"fallback": True},
                    audio=audio,
                )
            raise
        dynamic_thread = response.get("thread_id")
        text = str(response.get("final_answer", "")).strip()
        if not text:
            text = beat.fallback_text or "(no response generated)"
        audio = self._maybe_synthesise(text, participant, options.use_tts)
        dynamic_telemetry = dict(response.get("telemetry", {}))
        if dynamic_thread:
            telemetry.setdefault("dynamic_threads", []).append(dynamic_thread)
        context[f"beat_{beat.id}_thread"] = dynamic_thread or ""
        context[f"{participant.id}_last_answer"] = text
        return ScenarioTurnResult(
            beat_id=beat.id,
            speaker=participant,
            text=text,
            kind=beat.kind,
            stage_direction=beat.stage_direction,
            emphasis=beat.emphasis,
            duration_ms=float(dynamic_telemetry.get("total_duration_ms")) if dynamic_telemetry.get("total_duration_ms") else None,
            dynamic_source_thread=dynamic_thread,
            telemetry=dynamic_telemetry,
            audio=audio,
        )

    def _maybe_synthesise(
        self,
        text: str,
        participant: ScenarioParticipant,
        use_tts: bool,
    ) -> Optional[TextToSpeechResult]:
        if not use_tts or not participant.voice or self.tts is None:
            return None
        try:
            result = self.tts.synthesise(text=text, voice=participant.voice)
        except WorkflowException:
            return None
        return result

    def _actor_from_principal(self, principal: Principal | None) -> Dict[str, object]:
        if principal is None:
            return {"id": "system", "roles": [], "scopes": []}
        return {
            "id": principal.subject,
            "tenant": principal.tenant_id,
            "client": principal.client_id,
            "roles": sorted(principal.roles),
            "scopes": sorted(principal.scopes),
        }


_scenario_engine: ScenarioEngine | None = None


def get_scenario_engine() -> ScenarioEngine:
    global _scenario_engine
    if _scenario_engine is None:
        _scenario_engine = ScenarioEngine()
    return _scenario_engine
