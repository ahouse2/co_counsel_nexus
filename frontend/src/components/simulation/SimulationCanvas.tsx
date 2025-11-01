import { useMemo, useState } from 'react';
import { Stage, Sprite, Container, Text, useTick, Graphics } from '@pixi/react';
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

const MOTION_VECTORS: Record<string, { x: number; y: number }> = {
  none: { x: 0, y: 0 },
  left: { x: -1, y: 0 },
  right: { x: 1, y: 0 },
  forward: { x: 0, y: -1 },
  back: { x: 0, y: 1 },
};

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
  const directorCue = activeTurn?.director;
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
    const overlayColor = directorCue?.lighting.palette?.[0] ?? '#1e293b';
    const overlayOpacity = Math.min(Math.max(directorCue?.lighting.intensity ?? 0.75, 0), 2) / 2;
    const expression = directorCue?.persona.expression ?? 'neutral';
    return (
      <div className="simulation-canvas" data-renderer="fallback">
        <div
          className="simulation-canvas__stage"
          style={{
            backgroundImage: assets.manifest ? `url(${assets.manifest.stage.background})` : undefined,
            width: stageWidth,
            height: stageHeight,
          }}
          data-expression={expression}
        >
          <div
            className="simulation-canvas__stage-lighting"
            style={{ backgroundColor: overlayColor, opacity: overlayOpacity }}
            aria-hidden="true"
          />
          {characters.map((character) => (
            <div
              key={character.id}
              className="simulation-canvas__avatar"
              style={{
                left: character.position.x,
                top: character.position.y,
                borderColor: character.accentColor,
                opacity: character.enabled ? 1 : 0.35,
                transform:
                  activeTurn?.speaker_id === character.id && directorCue
                    ? `translate(${(MOTION_VECTORS[directorCue.motion.direction] ?? MOTION_VECTORS.none).x * 6}px, ${
                        (MOTION_VECTORS[directorCue.motion.direction] ?? MOTION_VECTORS.none).y * 6
                      }px)`
                    : undefined,
              }}
              data-active={activeTurn?.speaker_id === character.id}
              data-expression={expression}
            >
              <span>{character.name}</span>
            </div>
          ))}
        </div>
        <CaptionPanel
          activeTurn={activeTurn}
          transcript={transcript}
          currentIndex={currentIndex}
        />
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
        directorCue={directorCue}
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
  directorCue,
}: {
  manifest: SimulationManifest;
  characters: CharacterRenderSpec[];
  activeTurn: ScenarioRunTurn | undefined;
  isPlaying: boolean;
  directorCue: ScenarioRunTurn['director'];
}): JSX.Element {
  const [pulse, setPulse] = useState(0);
  const motionTempo = directorCue?.motion.tempo ?? 0.6;
  useTick((delta) => {
    if (!isPlaying) {
      return;
    }
    const speed = Math.max(0.1, motionTempo * 0.1);
    setPulse((value) => (value + delta * speed) % (Math.PI * 2));
  });
  const stageWidth = manifest.stage.width;
  const stageHeight = manifest.stage.height;
  const backgroundImage = manifest.stage.background;
  const nameplateStyle = useMemo(() => {
    const fill = directorCue?.lighting.palette?.[1] ?? '#e2e8f0';
    return new TextStyle({
      fill,
      fontSize: 18,
      fontWeight: '600',
    });
  }, [directorCue?.lighting.palette]);
  const overlayAlpha = useMemo(() => {
    if (!directorCue) {
      return 0;
    }
    return Math.min(0.65, Math.max(0, directorCue.lighting.intensity - 0.4));
  }, [directorCue]);
  const overlayColor = directorCue?.lighting.palette?.[0] ?? '#1e293b';

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
        {overlayAlpha > 0 ? (
          <Graphics
            draw={(graphics) => {
              graphics.clear();
              graphics.beginFill(Number.parseInt(overlayColor.replace('#', ''), 16), overlayAlpha);
              graphics.drawRect(0, 0, stageWidth, stageHeight);
              graphics.endFill();
            }}
          />
        ) : null}
        {characters.map((character) => {
          const isActive = activeTurn?.speaker_id === character.id;
          const vector = directorCue ? MOTION_VECTORS[directorCue.motion.direction] ?? MOTION_VECTORS.none : MOTION_VECTORS.none;
          const motionScale = directorCue?.motion.intensity ?? 0.35;
          const wobble = isActive ? 1 + Math.sin(pulse) * motionScale * 0.08 : 1;
          const tint = isActive
            ? Number.parseInt((directorCue?.lighting.palette?.[1] ?? character.accentColor).replace('#', ''), 16) || undefined
            : undefined;
          const offsetMagnitude = isActive ? Math.sin(pulse) * motionScale * 12 : 0;
          const offsetX = vector.x * offsetMagnitude;
          const offsetY = vector.y * offsetMagnitude;
          const expressionScale = isActive ? 1 + (directorCue?.persona.confidence ?? 0.6) * 0.05 : 1;
          return (
            <Container
              key={character.id}
              x={character.position.x + offsetX}
              y={character.position.y + offsetY}
              sortableChildren
            >
              {character.sprite ? (
                <Sprite
                  image={character.sprite}
                  anchor={0.5}
                  scale={wobble * expressionScale}
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
  const director = activeTurn?.director;
  const emotionalTone = director?.emotional_tone ?? 'neutral';
  return (
    <div className="simulation-canvas__captions" role="status" aria-live="polite">
      <div className="simulation-canvas__caption-line">
        <strong>{activeTurn?.speaker?.name ?? 'Awaiting simulation'}</strong>
        {activeTurn?.stage_direction ? <span className="stage-direction">({activeTurn.stage_direction})</span> : null}
      </div>
      <p>{activeTurn?.text ?? 'Run the simulation to generate dialogue.'}</p>
      {director?.counter_argument ? (
        <p className="simulation-canvas__counter-argument">Counter: {director.counter_argument}</p>
      ) : null}
      <footer>
        <span>
          Beat {clampedIndex >= 0 ? clampedIndex + 1 : 0}/{total}
        </span>
        <span>{remaining > 0 ? `${remaining} exchanges remaining` : 'End of script'}</span>
        <span className="simulation-canvas__emotional-tone">Tone: {emotionalTone}</span>
      </footer>
    </div>
  );
}
