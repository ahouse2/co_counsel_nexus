from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from uuid import uuid4

from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

from ..config import get_settings
from ..scenarios import ScenarioDefinition, ScenarioRegistry, ScenarioRegistryError
from ..scenarios.schema import DynamicBeat, ScenarioParticipant, ScriptedBeat
from ..security.authz import Principal
from ..storage.agent_memory_store import AgentMemoryStore, ScenarioRunRecord
from .agents import AgentsService, get_agents_service
from .errors import WorkflowAbort, WorkflowComponent, WorkflowError, WorkflowException
from .tts import TextToSpeechResult, TextToSpeechService, get_tts_service


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _safe_float(value: object, fallback: float) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback


def _safe_palette(value: object, fallback: List[str]) -> List[str]:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return fallback


@dataclass(slots=True)
class ScenarioDirectorMotion:
    direction: str
    intensity: float
    tempo: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "direction": self.direction,
            "intensity": round(self.intensity, 3),
            "tempo": round(self.tempo, 3),
        }

    def apply(self, override: Dict[str, object]) -> "ScenarioDirectorMotion":
        direction = str(override.get("direction", self.direction))
        intensity = _clamp(_safe_float(override.get("intensity", self.intensity), self.intensity), 0.0, 3.0)
        tempo = _clamp(_safe_float(override.get("tempo", self.tempo), self.tempo), 0.1, 3.0)
        return replace(self, direction=direction, intensity=intensity, tempo=tempo)


@dataclass(slots=True)
class ScenarioDirectorLighting:
    preset: str
    palette: List[str]
    intensity: float
    focus: float
    ambient: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "preset": self.preset,
            "palette": list(self.palette),
            "intensity": round(self.intensity, 3),
            "focus": round(self.focus, 3),
            "ambient": round(self.ambient, 3),
        }

    def apply(self, override: Dict[str, object]) -> "ScenarioDirectorLighting":
        preset = str(override.get("preset", self.preset))
        palette = _safe_palette(override.get("palette"), self.palette)
        intensity = _clamp(_safe_float(override.get("intensity", self.intensity), self.intensity), 0.0, 2.0)
        focus = _clamp(_safe_float(override.get("focus", self.focus), self.focus), 0.0, 2.0)
        ambient = _clamp(_safe_float(override.get("ambient", self.ambient), self.ambient), 0.0, 2.0)
        return replace(self, preset=preset, palette=palette, intensity=intensity, focus=focus, ambient=ambient)


@dataclass(slots=True)
class ScenarioDirectorPersona:
    expression: str
    vocal_register: str
    confidence: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "expression": self.expression,
            "vocal_register": self.vocal_register,
            "confidence": round(self.confidence, 3),
        }

    def apply(self, override: Dict[str, object]) -> "ScenarioDirectorPersona":
        expression = str(override.get("expression", self.expression))
        vocal_register = str(override.get("vocal_register", self.vocal_register))
        confidence = _clamp(_safe_float(override.get("confidence", self.confidence), self.confidence), 0.0, 1.0)
        return replace(self, expression=expression, vocal_register=vocal_register, confidence=confidence)


@dataclass(slots=True)
class ScenarioDirectorBeatPlan:
    beat_id: str
    emotional_tone: str
    counter_template: Optional[str]
    lighting: ScenarioDirectorLighting
    motion: ScenarioDirectorMotion
    persona: ScenarioDirectorPersona

    def to_dict(self, *, include_template: bool = True) -> Dict[str, object]:
        payload = {
            "beat_id": self.beat_id,
            "emotional_tone": self.emotional_tone,
            "lighting": self.lighting.to_dict(),
            "motion": self.motion.to_dict(),
            "persona": self.persona.to_dict(),
        }
        if include_template:
            payload["counter_template"] = self.counter_template
        return payload

    def apply_override(self, override: Dict[str, object]) -> "ScenarioDirectorBeatPlan":
        counter_template = override.get("counter_argument", self.counter_template)
        emotional_tone = str(override.get("emotional_tone", self.emotional_tone))
        lighting_override = override.get("lighting", {})
        motion_override = override.get("motion", {})
        persona_override = override.get("persona", {})
        if not isinstance(lighting_override, dict):
            lighting_override = {}
        if not isinstance(motion_override, dict):
            motion_override = {}
        if not isinstance(persona_override, dict):
            persona_override = {}
        return ScenarioDirectorBeatPlan(
            beat_id=self.beat_id,
            emotional_tone=emotional_tone,
            counter_template=str(counter_template) if counter_template is not None else None,
            lighting=self.lighting.apply(lighting_override),
            motion=self.motion.apply(motion_override),
            persona=self.persona.apply(persona_override),
        )


@dataclass(slots=True)
class ScenarioDirectorBeatCue:
    beat_id: str
    emotional_tone: str
    counter_argument: Optional[str]
    lighting: ScenarioDirectorLighting
    motion: ScenarioDirectorMotion
    persona: ScenarioDirectorPersona

    def to_dict(self) -> Dict[str, object]:
        return {
            "beat_id": self.beat_id,
            "emotional_tone": self.emotional_tone,
            "counter_argument": self.counter_argument,
            "lighting": self.lighting.to_dict(),
            "motion": self.motion.to_dict(),
            "persona": self.persona.to_dict(),
        }


@dataclass(slots=True)
class ScenarioDirectorManifest:
    version: str
    beats: Dict[str, ScenarioDirectorBeatPlan]

    def to_dict(self, *, include_templates: bool = True) -> Dict[str, object]:
        return {
            "version": self.version,
            "beats": {
                beat_id: plan.to_dict(include_template=include_templates)
                for beat_id, plan in self.beats.items()
            },
        }

    def apply_overrides(self, overrides: Dict[str, Dict[str, object]]) -> "ScenarioDirectorManifest":
        updated: Dict[str, ScenarioDirectorBeatPlan] = {}
        for beat_id, plan in self.beats.items():
            override = overrides.get(beat_id)
            if override:
                updated[beat_id] = plan.apply_override(override)
            else:
                updated[beat_id] = plan
        return ScenarioDirectorManifest(version=self.version, beats=updated)


class _TemplateDefaults(dict):
    def __missing__(self, key: str) -> str:  # pragma: no cover - defensive
        return "{" + key + "}"


class ScenarioDirector:
    """Derives cinematic and argumentative cues for scenario beats."""

    VERSION = "1.0"

    def compose_manifest(self, scenario: ScenarioDefinition) -> ScenarioDirectorManifest:
        beats: Dict[str, ScenarioDirectorBeatPlan] = {}
        previous_speaker: Optional[str] = None
        for beat in scenario.beats:
            tone = self._derive_tone(beat)
            lighting = self._derive_lighting(tone)
            motion = self._derive_motion(tone, beat.stage_direction or "")
            persona = self._derive_persona(tone, beat.stage_direction or "")
            template = self._derive_counter_template(beat, previous_speaker)
            beats[beat.id] = ScenarioDirectorBeatPlan(
                beat_id=beat.id,
                emotional_tone=tone,
                counter_template=template,
                lighting=lighting,
                motion=motion,
                persona=persona,
            )
            previous_speaker = beat.speaker
        return ScenarioDirectorManifest(version=self.VERSION, beats=beats)

    def runtime_cue(
        self,
        manifest: ScenarioDirectorManifest,
        beat_id: str,
        context: Dict[str, str],
        *,
        speaker: ScenarioParticipant,
        text: str,
        previous_text: Optional[str],
    ) -> ScenarioDirectorBeatCue:
        plan = manifest.beats.get(beat_id)
        if plan is None:
            plan = ScenarioDirectorBeatPlan(
                beat_id=beat_id,
                emotional_tone="neutral",
                counter_template=None,
                lighting=self._derive_lighting("neutral"),
                motion=self._derive_motion("neutral", ""),
                persona=self._derive_persona("neutral", ""),
            )
        render_context = _TemplateDefaults({k: str(v) for k, v in context.items()})
        render_context["current_line"] = text
        render_context.setdefault("speaker_name", speaker.name)
        if previous_text:
            render_context["previous_line"] = previous_text
        counter_argument = None
        if plan.counter_template:
            counter_argument = plan.counter_template.format_map(render_context)
        return ScenarioDirectorBeatCue(
            beat_id=plan.beat_id,
            emotional_tone=plan.emotional_tone,
            counter_argument=counter_argument,
            lighting=plan.lighting,
            motion=plan.motion,
            persona=plan.persona,
        )

    def _derive_tone(self, beat: ScriptedBeat | DynamicBeat) -> str:
        emphasis = (beat.emphasis or "").lower()
        direction = (beat.stage_direction or "").lower()
        if any(keyword in emphasis for keyword in ("aggressive", "heated", "fiery")) or "slam" in direction:
            return "confrontational"
        if any(keyword in emphasis for keyword in ("empathetic", "soothing", "reassuring")):
            return "empathetic"
        if any(keyword in emphasis for keyword in ("urgent", "rapid", "pressing")) or "paces" in direction:
            return "urgent"
        if any(keyword in direction for keyword in ("pause", "consider", "reflect")):
            return "contemplative"
        if "confident" in emphasis or "steady" in direction:
            return "confident"
        if "hesitant" in emphasis:
            return "hesitant"
        if "assertive" in emphasis:
            return "assertive"
        return "neutral"

    def _derive_lighting(self, tone: str) -> ScenarioDirectorLighting:
        palette_map = {
            "confrontational": ["#fca5a5", "#7f1d1d"],
            "empathetic": ["#a7f3d0", "#0f766e"],
            "urgent": ["#fcd34d", "#b45309"],
            "contemplative": ["#d8b4fe", "#6b21a8"],
            "confident": ["#bfdbfe", "#1d4ed8"],
            "hesitant": ["#cbd5f5", "#475569"],
            "assertive": ["#fef08a", "#c2410c"],
            "neutral": ["#e2e8f0", "#1e293b"],
        }
        intensity_map = {
            "confrontational": (1.1, 1.3, 0.5),
            "empathetic": (0.85, 1.2, 0.7),
            "urgent": (1.0, 1.4, 0.4),
            "contemplative": (0.7, 1.0, 0.8),
            "confident": (0.95, 1.25, 0.6),
            "hesitant": (0.6, 0.9, 0.9),
            "assertive": (1.0, 1.3, 0.5),
            "neutral": (0.75, 1.0, 0.65),
        }
        palette = palette_map.get(tone, palette_map["neutral"])
        intensity, focus, ambient = intensity_map.get(tone, intensity_map["neutral"])
        return ScenarioDirectorLighting(
            preset=tone,
            palette=palette,
            intensity=intensity,
            focus=focus,
            ambient=ambient,
        )

    def _derive_motion(self, tone: str, stage_direction: str) -> ScenarioDirectorMotion:
        direction = "none"
        if any(keyword in stage_direction.lower() for keyword in ("left", "clockwise")):
            direction = "left"
        elif any(keyword in stage_direction.lower() for keyword in ("right", "counter")):
            direction = "right"
        elif "forward" in stage_direction.lower() or "approach" in stage_direction.lower():
            direction = "forward"
        elif "back" in stage_direction.lower() or "retreat" in stage_direction.lower():
            direction = "back"
        tone_intensity = {
            "confrontational": 1.4,
            "urgent": 1.2,
            "assertive": 1.0,
            "confident": 0.9,
            "empathetic": 0.7,
            "contemplative": 0.5,
            "hesitant": 0.4,
            "neutral": 0.3,
        }
        tone_tempo = {
            "confrontational": 1.3,
            "urgent": 1.2,
            "assertive": 1.0,
            "confident": 0.95,
            "empathetic": 0.8,
            "contemplative": 0.6,
            "hesitant": 0.55,
            "neutral": 0.5,
        }
        intensity = tone_intensity.get(tone, tone_intensity["neutral"])
        tempo = tone_tempo.get(tone, tone_tempo["neutral"])
        return ScenarioDirectorMotion(direction=direction, intensity=intensity, tempo=tempo)

    def _derive_persona(self, tone: str, stage_direction: str) -> ScenarioDirectorPersona:
        register_map = {
            "confrontational": ("command", 0.65),
            "urgent": ("brisk", 0.6),
            "assertive": ("steady", 0.7),
            "confident": ("resonant", 0.8),
            "empathetic": ("warm", 0.9),
            "contemplative": ("measured", 0.75),
            "hesitant": ("soft", 0.4),
            "neutral": ("neutral", 0.6),
        }
        expression = tone
        if "smile" in stage_direction.lower():
            expression = "reassuring"
        elif "frown" in stage_direction.lower() or "glare" in stage_direction.lower():
            expression = "stern"
        vocal_register, confidence = register_map.get(tone, register_map["neutral"])
        return ScenarioDirectorPersona(expression=expression, vocal_register=vocal_register, confidence=confidence)

    def _derive_counter_template(
        self,
        beat: ScriptedBeat | DynamicBeat,
        previous_speaker: Optional[str],
    ) -> Optional[str]:
        stage = (beat.stage_direction or "").strip()
        emphasis = (beat.emphasis or "").strip()
        opponent = previous_speaker or "opposing counsel"
        if isinstance(beat, DynamicBeat):
            focus = beat.delegate or opponent
            return (
                "If {speaker_name} faces pushback from "
                f"{focus}, reiterate {{issue}} and contrast with {{primary_document}}."
            )
        if stage:
            return f"Anticipate {opponent}'s reply by grounding the point in {{timeline_event}} while {stage.lower()}."
        if emphasis:
            return f"Lean into the {emphasis.lower()} tone and restate {{witness_fact}} to undercut {opponent}."
        return None


_tracer = trace.get_tracer(__name__)
_meter = metrics.get_meter(__name__)

_scenario_runs_counter = _meter.create_counter(
    "scenario_runs_total",
    unit="1",
    description="Simulation runs executed",
)
_scenario_run_duration = _meter.create_histogram(
    "scenario_run_duration_ms",
    unit="ms",
    description="Duration of scenario runs",
)
_scenario_beats_counter = _meter.create_counter(
    "scenario_beats_total",
    unit="1",
    description="Beats processed within scenarios",
)
_scenario_beat_duration = _meter.create_histogram(
    "scenario_beat_duration_ms",
    unit="ms",
    description="Duration of individual scenario beats",
)
_scenario_tts_counter = _meter.create_counter(
    "scenario_tts_synth_total",
    unit="1",
    description="Count of TTS synthesis events during scenarios",
)


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
    director_overrides: Dict[str, Dict[str, object]] = field(default_factory=dict)


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
    director: Optional["ScenarioDirectorBeatCue"] = None


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
        self.director = ScenarioDirector()

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
        run_started = time.perf_counter()
        director_manifest = self.director.compose_manifest(scenario)
        if options.director_overrides:
            director_manifest = director_manifest.apply_overrides(options.director_overrides)
        telemetry["director_manifest"] = director_manifest.to_dict()
        telemetry["director_runtime"] = []
        previous_text: Optional[str] = None

        with _tracer.start_as_current_span("scenario.run") as span:
            span.set_attribute("scenario.id", scenario.id)
            span.set_attribute("scenario.case_id", options.case_id)
            span.set_attribute("scenario.use_tts", options.use_tts)
            try:
                for beat in scenario.beats:
                    beat_started = time.perf_counter()
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
                    elapsed = (time.perf_counter() - beat_started) * 1000.0
                    metric_attributes = {
                        "kind": result.kind,
                        "scenario_id": scenario.id,
                    }
                    _scenario_beats_counter.add(1, attributes=metric_attributes)
                    _scenario_beat_duration.record(elapsed, attributes=metric_attributes)
                    beat_telemetry = {
                        "beat_id": beat.id,
                        "kind": result.kind,
                        "speaker": result.speaker.id,
                        "duration_ms": round(elapsed, 2),
                        "thread_id": result.dynamic_source_thread,
                    }
                    telemetry.setdefault("beats", []).append(beat_telemetry)
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
                        _scenario_tts_counter.add(1, attributes={"scenario_id": scenario.id})
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
                    director_cue = self.director.runtime_cue(
                        director_manifest,
                        beat.id,
                        context,
                        speaker=result.speaker,
                        text=result.text,
                        previous_text=previous_text,
                    )
                    result.director = director_cue
                    context[f"beat_{beat.id}_counter_argument"] = director_cue.counter_argument or ""
                    turn_payload["director"] = director_cue.to_dict()
                    beat_telemetry["director"] = director_cue.to_dict()
                    telemetry["director_runtime"].append(director_cue.to_dict())
                    previous_text = result.text
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
                        "director_overrides": options.director_overrides,
                        "director_manifest": director_manifest.to_dict(),
                    },
                    transcript=transcript,
                    telemetry=telemetry,
                )
                self.memory.write_scenario(record)
                duration_ms = (time.perf_counter() - run_started) * 1000.0
                attributes = {
                    "status": "completed",
                    "use_tts": options.use_tts,
                    "scenario_id": scenario.id,
                }
                _scenario_run_duration.record(duration_ms, attributes=attributes)
                _scenario_runs_counter.add(1, attributes=attributes)
                span.set_attribute("scenario.duration_ms", duration_ms)
                span.set_attribute("scenario.beats_processed", len(scenario.beats))
                span.set_status(Status(StatusCode.OK))
                return {
                    "run_id": run_id,
                    "scenario": scenario.model_dump(mode="json"),
                    "transcript": transcript,
                    "telemetry": telemetry,
                }
            except WorkflowAbort as exc:
                _scenario_runs_counter.add(
                    1,
                    attributes={
                        "status": "failed",
                        "use_tts": options.use_tts,
                        "scenario_id": scenario.id,
                    },
                )
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, description=str(exc.error.message)))
                raise
            except Exception as exc:
                _scenario_runs_counter.add(
                    1,
                    attributes={
                        "status": "error",
                        "use_tts": options.use_tts,
                        "scenario_id": scenario.id,
                    },
                )
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, description=str(exc)))
                raise

    def director_manifest(self, scenario: ScenarioDefinition) -> ScenarioDirectorManifest:
        return self.director.compose_manifest(scenario)

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

        speakers = {beat.speaker for beat in scenario.beats}
        missing_active = sorted(speaker for speaker in speakers if speaker not in active)
        if missing_active:
            inactive = ", ".join(missing_active)
            raise WorkflowAbort(
                WorkflowError(
                    component=WorkflowComponent.SCENARIO,
                    code="SCENARIO_PARTICIPANT_INACTIVE",
                    message=(
                        "Scenario configuration deselected participants required for beats: "
                        f"{inactive}"
                    ),
                )
            )
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
