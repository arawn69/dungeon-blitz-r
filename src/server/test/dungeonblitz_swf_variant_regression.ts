import { strict as assert } from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { buildDungeonBlitzSwfVariantBuffer } from '../core/DungeonBlitzSwf';
import { parseAbc, parseSwf } from '../scripts/swfPatchUtils';

const BASE_SWF_PATH = path.resolve(__dirname, '../../client/content/localhost/p/cbp/DungeonBlitz.swf');

function getStringMatches(swfPath: string, target: string): number[] {
    const ctx = parseSwf(swfPath);
    const abc = parseAbc(ctx);
    const matches: number[] = [];

    for (let index = 1; index < abc.stringValues.length; index++) {
        if (abc.stringValues[index] === target) {
            matches.push(index);
        }
    }

    return matches;
}

function withTempSwf(buffer: Buffer, callback: (tempPath: string) => void): void {
    const tempPath = path.join(os.tmpdir(), `dungeonblitz-variant-${process.pid}-${Date.now()}-${Math.random()}.swf`);
    fs.writeFileSync(tempPath, buffer);
    try {
        callback(tempPath);
    } finally {
        fs.rmSync(tempPath, { force: true });
    }
}

function testLocalVariantUsesLocalhostAndPort8000(): void {
    const buffer = buildDungeonBlitzSwfVariantBuffer(BASE_SWF_PATH, 'local');
    withTempSwf(buffer, (tempPath) => {
        assert.deepEqual(getStringMatches(tempPath, 'localhost'), [14996, 15564]);
        assert.deepEqual(getStringMatches(tempPath, ':8000/p/'), [2547]);
        assert.deepEqual(getStringMatches(tempPath, 'http://localhost:8000/p/cbp/DungeonBlitz.swf?fv=cbq&gv=cbp'), [15565, 15566]);
        assert.deepEqual(getStringMatches(tempPath, '100.100.146.54'), []);
    });
}

function testMultiplayerVariantUsesRemoteHostAndDefaultAssetPath(): void {
    const buffer = buildDungeonBlitzSwfVariantBuffer(BASE_SWF_PATH, 'multiplayer');
    withTempSwf(buffer, (tempPath) => {
        assert.deepEqual(getStringMatches(tempPath, '100.100.146.54'), [14996, 15564]);
        assert.deepEqual(getStringMatches(tempPath, '/p/'), [2547]);
        assert.deepEqual(getStringMatches(tempPath, 'http://100.100.146.54/p/cbp/DungeonBlitz.swf?fv=cbq&gv=cbp'), [15565, 15566]);
        assert.deepEqual(getStringMatches(tempPath, 'localhost'), []);
        assert.deepEqual(getStringMatches(tempPath, ':8000/p/'), []);
    });
}

function main(): void {
    testLocalVariantUsesLocalhostAndPort8000();
    testMultiplayerVariantUsesRemoteHostAndDefaultAssetPath();
    console.log('dungeonblitz_swf_variant_regression: ok');
}

main();
