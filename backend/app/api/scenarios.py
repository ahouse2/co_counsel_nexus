
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status

from ..models.api import (
    ScenarioDefinitionModel,
    ScenarioListResponse,
    ScenarioRunRequestModel,
    ScenarioRunResponseModel,
    TextToSpeechRequest,
    TextToSpeechResponse,
)
from ..services.scenarios import get_scenario_engine, ScenarioRunOptions, ScenarioEvidenceBinding
from ..services.tts import TextToSpeechService, get_tts_service
from ..services.errors import WorkflowException
from ..security.authz import Principal
from ..security.dependencies import authorize_agents_read, authorize_agents_run
import base64

router = APIRouter()

def _raise_workflow_exception(exc: WorkflowException) -> None:
    status_code = exc.status_code or http_status_for_error(exc.error)
    raise HTTPException(status_code=status_code, detail=exc.error.to_dict()) from exc

@router.get("/scenarios", response_model=ScenarioListResponse)
def scenarios_list(
    engine = Depends(get_scenario_engine),
    principal: Principal = Depends(authorize_agents_read),
) -> ScenarioListResponse:
    _ = principal
    metadata = engine.list_metadata()
    return ScenarioListResponse(scenarios=[_scenario_metadata_model(item) for item in metadata])


@router.get("/scenarios/{scenario_id}", response_model=ScenarioDefinitionModel)
def scenarios_detail(
    scenario_id: str,
    engine = Depends(get_scenario_engine),
    principal: Principal = Depends(authorize_agents_read),
) -> ScenarioDefinitionModel:
    _ = principal
    try:
        definition = engine.get(scenario_id)
    except WorkflowException as exc:
        _raise_workflow_exception(exc)
    manifest = engine.director_manifest(definition)
    return _scenario_definition_model(definition, manifest)


@router.post("/scenarios/run", response_model=ScenarioRunResponseModel)
def scenarios_run(
    payload: ScenarioRunRequestModel,
    engine = Depends(get_scenario_engine),
    principal: Principal = Depends(authorize_agents_run),
) -> ScenarioRunResponseModel:
    options = _scenario_run_options(payload)
    try:
        definition = engine.get(options.scenario_id)
        result = engine.run(options, principal=principal)
    except WorkflowException as exc:
        _raise_workflow_exception(exc)
    transcript_models = [ScenarioRunTurnModel.model_validate(turn) for turn in result.get("transcript", [])]
    manifest = engine.director_manifest(definition)
    definition_model = _scenario_definition_model(definition, manifest)
    telemetry = dict(result.get("telemetry", {}))
    return ScenarioRunResponseModel(
        run_id=str(result.get("run_id")),
        scenario=definition_model,
        transcript=transcript_models,
        telemetry=telemetry,
    )


def _tts_service_dependency() -> TextToSpeechService:
    service = get_tts_service(optional=True)
    if service is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TTS service not configured")
    return service


@router.post("/tts/speak", response_model=TextToSpeechResponse)
def tts_speak(
    payload: TextToSpeechRequest,
    service: TextToSpeechService = Depends(_tts_service_dependency),
    principal: Principal = Depends(authorize_agents_run),
) -> TextToSpeechResponse:
    _ = principal
    try:
        result = service.synthesise(text=payload.text, voice=payload.voice)
    except WorkflowException as exc:
        _raise_workflow_exception(exc)
    return TextToSpeechResponse(
        voice=result.voice,
        mime_type=result.content_type,
        base64=base64.b64encode(result.audio_bytes).decode("ascii"),
        cache_hit=result.cache_hit,
        sha256=result.sha256,
    )
