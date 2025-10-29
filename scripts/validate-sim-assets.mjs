#!/usr/bin/env node
import { access, readFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const publicRoot = path.join(repoRoot, 'frontend', 'public');
const simulationsRoot = path.join(publicRoot, 'simulations');
const manifestPath = path.join(simulationsRoot, 'manifest.json');

async function ensureFile(filePath, label) {
  try {
    await access(filePath, constants.F_OK);
  } catch (error) {
    throw new Error(`Missing ${label} at ${path.relative(repoRoot, filePath)}`);
  }
}

function ensureSvg(content, label) {
  if (!content.includes('<svg')) {
    throw new Error(`${label} is not a valid SVG document`);
  }
  const hasDimensions = /<svg[^>]*(width|viewBox)/i.test(content);
  if (!hasDimensions) {
    throw new Error(`${label} is missing width or viewBox attributes`);
  }
}

async function validateManifest() {
  const raw = await readFile(manifestPath, 'utf-8');
  const manifest = JSON.parse(raw);
  if (manifest.version !== 1) {
    throw new Error(`Unsupported simulation manifest version: ${manifest.version}`);
  }
  const stage = manifest.stage;
  if (!stage || typeof stage.width !== 'number' || typeof stage.height !== 'number') {
    throw new Error('Stage dimensions must be defined in simulation manifest');
  }
  if (!stage.background) {
    throw new Error('Stage background asset missing from simulation manifest');
  }
  const backgroundPath = path.join(publicRoot, stage.background.replace(/^\//, ''));
  await ensureFile(backgroundPath, 'stage background');
  const backgroundContent = await readFile(backgroundPath, 'utf-8');
  ensureSvg(backgroundContent, 'Stage background');
  const positions = stage.characterPositions || {};
  const characters = manifest.characters || {};
  for (const [id, character] of Object.entries(characters)) {
    if (!character.sprite) {
      throw new Error(`Character ${id} missing sprite reference`);
    }
    const spritePath = path.join(publicRoot, character.sprite.replace(/^\//, ''));
    await ensureFile(spritePath, `sprite for ${id}`);
    const spriteContent = await readFile(spritePath, 'utf-8');
    ensureSvg(spriteContent, `Sprite for ${id}`);
    if (!positions[id]) {
      throw new Error(`Character position missing for ${id}`);
    }
  }
  console.log('✓ Simulation assets validated');
}

async function main() {
  try {
    await validateManifest();
  } catch (error) {
    console.error(`Simulation asset validation failed: ${error.message}`);
    process.exit(1);
  }
}

await main();
