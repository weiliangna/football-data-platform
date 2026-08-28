import test from 'node:test';
import assert from 'node:assert/strict';
import { clamp,pct } from '../dist/js/utils/format.js';
test('format helpers',()=>{assert.equal(pct(12.34),'12.3%');assert.equal(clamp(120),100);assert.equal(clamp(-1),0)});
