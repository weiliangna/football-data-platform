import test from 'node:test';
import assert from 'node:assert/strict';
import { renderHeat } from '../dist/js/pages/heat.js';

const plays = ['胜平负', '让球胜平负', '半全场', '比分'];

test('all heat play cards share the same row structure', () => {
  for (const play of plays) {
    const html = renderHeat({ play });
    assert.equal((html.match(/class="heat-insight-row"/g) || []).length, 15);
    assert.equal((html.match(/class="heat-insight-pick"/g) || []).length, 15);
    assert.equal((html.match(/class="heat-insight-count"/g) || []).length, 15);
    assert.match(html, new RegExp(`center-analysis ${play === '胜平负' ? 'accent-blue' : play === '让球胜平负' ? 'rose' : play === '半全场' ? 'orange' : 'teal'}`));
    assert.doesNotMatch(html, /hot-play-card brand/);
  }
});
