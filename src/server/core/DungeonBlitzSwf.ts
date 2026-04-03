import * as zlib from 'zlib';
import {
    applyPatchesToBody,
    parseAbc,
    parseSwf,
    writeU30
} from '../scripts/swfPatchUtils';

export type DungeonBlitzSwfMode = 'local' | 'multiplayer';

const LOCAL_HOST = 'localhost';
const REMOTE_HOST = '100.100.146.54';
const LOCAL_ASSET_PATH = ':8000/p/';
const REMOTE_ASSET_PATH = '/p/';
const LOCAL_REFRESH_URL = 'http://localhost:8000/p/cbp/DungeonBlitz.swf?fv=cbq&gv=cbp';
const LOCAL_REFRESH_URL_LEGACY = 'http://localhost/p/cbp/DungeonBlitz.swf?fv=cbq&gv=cbp';
const REMOTE_REFRESH_URL = 'http://100.100.146.54/p/cbp/DungeonBlitz.swf?fv=cbq&gv=cbp';

type StringReplacement = {
    oldValue: string;
    newValue: string;
};

function getReplacements(mode: DungeonBlitzSwfMode): StringReplacement[] {
    if (mode === 'local') {
        return [
            { oldValue: REMOTE_HOST, newValue: LOCAL_HOST },
            { oldValue: REMOTE_ASSET_PATH, newValue: LOCAL_ASSET_PATH },
            { oldValue: REMOTE_REFRESH_URL, newValue: LOCAL_REFRESH_URL },
            { oldValue: LOCAL_REFRESH_URL_LEGACY, newValue: LOCAL_REFRESH_URL }
        ];
    }

    return [
        { oldValue: LOCAL_HOST, newValue: REMOTE_HOST },
        { oldValue: LOCAL_ASSET_PATH, newValue: REMOTE_ASSET_PATH },
        { oldValue: LOCAL_REFRESH_URL, newValue: REMOTE_REFRESH_URL },
        { oldValue: LOCAL_REFRESH_URL_LEGACY, newValue: REMOTE_REFRESH_URL }
    ];
}

export function buildDungeonBlitzSwfVariantBuffer(
    swfPath: string,
    mode: DungeonBlitzSwfMode
): Buffer {
    const ctx = parseSwf(swfPath);
    const abc = parseAbc(ctx);
    const patches = [];

    for (const replacement of getReplacements(mode)) {
        for (let index = 1; index < abc.stringValues.length; index++) {
            if (abc.stringValues[index] !== replacement.oldValue) {
                continue;
            }

            const replacementBytes = Buffer.from(replacement.newValue, 'utf8');
            const originalBytes = Buffer.from(replacement.oldValue, 'utf8');
            patches.push({
                key: `string:${replacement.oldValue}:${index}`,
                start: abc.stringLenPositions[index],
                end: abc.stringDataPositions[index] + originalBytes.length,
                data: Buffer.concat([writeU30(replacementBytes.length), replacementBytes]),
                detail: `${replacement.oldValue} -> ${replacement.newValue}`
            });
        }
    }

    const { body, delta } = applyPatchesToBody(ctx.body, patches);
    const outBody = Buffer.from(body);
    if (delta !== 0) {
        outBody.writeUInt32LE(ctx.doabcLen + delta, ctx.doabcLenFieldPos);
    }

    const header = Buffer.alloc(8);
    header.write(ctx.signature, 0, 'ascii');
    header[3] = ctx.version;
    header.writeUInt32LE(8 + outBody.length, 4);

    return ctx.signature === 'CWS'
        ? Buffer.concat([header, zlib.deflateSync(outBody)])
        : Buffer.concat([header, outBody]);
}
