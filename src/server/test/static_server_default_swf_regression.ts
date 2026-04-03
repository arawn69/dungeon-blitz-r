import { strict as assert } from 'assert';
import * as fs from 'fs';
import * as path from 'path';
import { StaticServer } from '../core/StaticServer';

function testStaticServerServesSingleSwfByDefault(): void {
    const server = new StaticServer();
    const selectedSwfPath = (server as any).getSelectedSwfPath() as string;
    const selectedSwfUrl = (server as any).getSelectedSwfUrl() as string;

    assert.equal(path.basename(selectedSwfPath), 'DungeonBlitz.swf');
    assert.equal(selectedSwfUrl, '/p/cbp/DungeonBlitz.swf?fv=cbq&gv=cbp');
    assert.equal(fs.existsSync(selectedSwfPath), true);
}

function main(): void {
    testStaticServerServesSingleSwfByDefault();
    console.log('static_server_default_swf_regression: ok');
}

main();
