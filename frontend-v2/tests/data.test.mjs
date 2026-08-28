import test from 'node:test';
import assert from 'node:assert/strict';
import { matches } from '../dist/js/services/dashboard.js';
import { plans } from '../dist/js/services/plans.js';
import { users } from '../dist/js/services/users.js';
test('local data services expose usable records',()=>{assert.ok(matches.length>=8);assert.ok(plans.length>=30);assert.ok(users.length>=10);assert.ok(matches.every(m=>m.home&&m.away&&m.status))});
