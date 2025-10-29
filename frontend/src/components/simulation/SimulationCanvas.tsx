import { useMemo, useState } from 'react';
import { Stage, Sprite, Container, Text, useTick } from '@pixi/react';
import { TextStyle } from '@pixi/text';
import { ScenarioDefinition, ScenarioRunTurn } from '@/types';
import { useSimulationAssets, type SimulationManifest } from '@/hooks/useSimulationAssets';

interface SimulationCanvasProps {
  scenario?: ScenarioDefinition;
  transcript?: ScenarioRunTurn[];
  enabledParticipants: Record<string, boolean>;
  activeIndex: number;
  isPlaying: boolean;
  forceFallback?: boolean;
}

interface CharacterRenderSpec {
  id: string;
  name: string;
  sprite: string;
  accentColor: string;
  position: { x: number; y: number };
  enabled: boolean;
}

const FALLBACK_STAGE = {
  width: 960,
  height: 540,
};

const placeholderStyleCache = new Map<string, TextStyle>();

function getPlaceholderStyle(accent: string): TextStyle {
  const cached = placeholderStyleCache.get(accent);
  if (cached) {
    return cached;
  }
  const style = new TextStyle({
    fill: accent,
    fontWeight: '600',
    fontSize: 24,
  });
  placeholderStyleCache.set(accent, style);
  return style;
}

function buildCharacterSpecs(
  scenario: ScenarioDefinition | undefined,
  enabledParticipants: Record<string, boolean>,
  manifest: ReturnType<typeof useSimulationAssets>['manifest']
): CharacterRenderSpec[] {
  if (!scenario || !manifest) {
    return [];
  }
  return scenario.participants.map((participant) => {
    const manifestEntry = manifest.characters[participant.id];
    const position = manifest.stage.characterPositions[participant.id] ?? { x: manifest.stage.width / 2, y: manifest.stage.height / 2 };
    return {
      id: participant.id,
      name: participant.name,
      sprite: participant.sprite || manifestEntry?.sprite || '',
      accentColor: participant.accent_color || manifestEntry?.accentColor || '#e2e8f0',
      position,
      enabled: enabledParticipants[participant.id] ?? true,
    };
  });
}

export function SimulationCanvas({
  scenario,
  transcript,
  enabledParticipants,
  activeIndex,
  isPlaying,
  forceFallback = false,
}: SimulationCanvasProps): JSX.Element {
  const assets = useSimulationAssets();

  const activeTurn = transcript?.[activeIndex];
  const characters = useMemo(
    () => buildCharacterSpecs(scenario, enabledParticipants, assets.manifest),
    [scenario, enabledParticipants, assets.manifest]
  );
  const currentIndex = useMemo(() => {
    if (!transcript || !activeTurn) {
      return -1;
    }
    return transcript.findIndex((turn) => turn.beat_id === activeTurn.beat_id);
  }, [activeTurn, transcript]);

  const isSimulatedEnvironment =
    typeof navigator !== 'undefined' && /jsdom/i.test(navigator.userAgent ?? '');
  const shouldFallback =
    forceFallback ||
    typeof window === 'undefined' ||
    isSimulatedEnvironment ||
    !assets.manifest ||
    assets.status !== 'loaded';

  if (shouldFallback) {
    const stageWidth = assets.manifest?.stage.width ?? FALLBACK_STAGE.width;
    const stageHeight = assets.manifest?.stage.height ?? FALLBACK_STAGE.height;
    return (
      <div className="simulation-canvas" data-renderer="fallback">
        <div
          className="simulation-canvas__stage"
          style={{
            backgroundImage: assets.manifest ? `url(${assets.manifest.stage.background})` : undefined,
            width: stageWidth,
            height: stageHeight,
          }}
        >
          {characters.map((character) => (
            <div
              key={character.id}
              className="simulation-canvas__avatar"
              style={{
                left: character.position.x,
                top: character.position.y,
                borderColor: character.accentColor,
                opacity: character.enabled ? 1 : 0.35,
              }}
              data-active={activeTurn?.speaker_id === character.id}
            >
              <span>{character.name}</span>
            </div>
          ))}
        </div>
        <CaptionPanel activeTurn={activeTurn} transcript={transcript} currentIndex={currentIndex} />
      </div>
    );
  }

  return (
    <div className="simulation-canvas" data-renderer="pixi">
      <PixiStageView
        manifest={assets.manifest!}
        characters={characters}
        activeTurn={activeTurn}
        isPlaying={isPlaying}
      />
      <CaptionPanel activeTurn={activeTurn} transcript={transcript} currentIndex={currentIndex} />
    </div>
  );
}

function PixiStageView({
  manifest,
  characters,
  activeTurn,
  isPlaying,
}: {
  manifest: SimulationManifest;
  characters: CharacterRenderSpec[];
  activeTurn: ScenarioRunTurn | undefined;
  isPlaying: boolean;
}): JSX.Element {
  const [pulse, setPulse] = useState(0);
  useTick((delta) => {
    if (!isPlaying) {
      return;
    }
    setPulse((value) => (value + delta * 0.075) % (Math.PI * 2));
  });
  const stageWidth = manifest.stage.width;
  const stageHeight = manifest.stage.height;
  const backgroundImage = manifest.stage.background;
  const nameplateStyle = useMemo(
    () =>
      new TextStyle({
        fill: '#e2e8f0',
        fontSize: 18,
        fontWeight: '600',
      }),
    []
  );

  return (
    <Stage
      width={stageWidth}
      height={stageHeight}
      options={{
        backgroundAlpha: 0,
        antialias: true,
      }}
    >
      <Container sortableChildren>
        {backgroundImage ? <Sprite image={backgroundImage} x={0} y={0} width={stageWidth} height={stageHeight} /> : null}
        {characters.map((character) => {
          const isActive = activeTurn?.speaker_id === character.id;
          const wobble = isActive ? 1 + Math.sin(pulse) * 0.08 : 1;
          const tint = isActive
            ? Number.parseInt(character.accentColor.replace('#', ''), 16) || undefined
            : undefined;
          return (
            <Container key={character.id} x={character.position.x} y={character.position.y} sortableChildren>
              {character.sprite ? (
                <Sprite
                  image={character.sprite}
                  anchor={0.5}
                  scale={wobble}
                  alpha={character.enabled ? 1 : 0.35}
                  tint={tint}
                />
              ) : (
                <Text
                  text={character.name}
                  anchor={0.5}
                  style={getPlaceholderStyle(character.accentColor)}
                />
              )}
              <Text
                text={character.name}
                anchor={0.5}
                y={80}
                style={nameplateStyle}
              />
            </Container>
          );
        })}
      </Container>
    </Stage>
  );
}

function CaptionPanel({
  activeTurn,
  transcript,
  currentIndex,
}: {
  activeTurn: ScenarioRunTurn | undefined;
  transcript: ScenarioRunTurn[] | undefined;
  currentIndex: number;
}): JSX.Element {
  const total = transcript?.length ?? 0;
  const clampedIndex = currentIndex >= 0 ? currentIndex : -1;
  const remaining = clampedIndex >= 0 && transcript ? Math.max(transcript.length - clampedIndex - 1, 0) : total;
  return (
    <div className="simulation-canvas__captions" role="status" aria-live="polite">
      <div className="simulation-canvas__caption-line">
        <strong>{activeTurn?.speaker?.name ?? 'Awaiting simulation'}</strong>
        {activeTurn?.stage_direction ? <span className="stage-direction">({activeTurn.stage_direction})</span> : null}
      </div>
      <p>{activeTurn?.text ?? 'Run the simulation to generate dialogue.'}</p>
      <footer>
        <span>
          Beat {clampedIndex >= 0 ? clampedIndex + 1 : 0}/{total}
        </span>
        <span>{remaining > 0 ? `${remaining} exchanges remaining` : 'End of script'}</span>
      </footer>
    </div>
  );
}
