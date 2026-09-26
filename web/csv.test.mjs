import test from 'node:test';
import assert from 'node:assert/strict';
import { COLUMNS, parseDelimited, autoMapping, mappedRows, validate, exportCsv, generateResearchIds } from './csv.mjs';

const row = {
  pt_id: 'p_1', research_id: 'r_00001', data_identifier: '0000000123',
  event_date: '20260102', encounter_start_date: '20260101', encounter_end_date: '20260110',
};

test('quoted CSV, BOM, and round trip preserve leading zeroes and Unicode', () => {
  const input = '\uFEFF' + COLUMNS.join(',') + '\r\n' +
    '"患者,一",r_00001,0000000123,20260102,20260101,20260110\r\n';
  const parsed = parseDelimited(input);
  assert.deepEqual(autoMapping(parsed[0]), [0, 1, 2, 3, 4, 5]);
  const mapped = mappedRows(parsed.slice(1), autoMapping(parsed[0]));
  assert.equal(mapped[0].pt_id, '患者,一');
  const output = exportCsv(mapped);
  assert.ok(output.startsWith('\uFEFF'));
  assert.deepEqual(parseDelimited(output), parsed);
});

test('TSV mapping and date normalization', () => {
  const parsed = parseDelimited('識別子\t開始\t終了\n123\t2026-01-01\t2026/01/10\n', '\t');
  const mapped = mappedRows(parsed.slice(1), [-1, -1, 0, -1, 1, 2]);
  const generated = generateResearchIds(mapped, { prefix: 'r_', digits: 5, start: 1 });
  const result = validate(generated);
  assert.deepEqual(result.errors, []);
  assert.equal(result.normalized[0].data_identifier, '0000000123');
  assert.equal(result.normalized[0].encounter_start_date, '20260101');
  assert.equal(result.normalized[0].encounter_end_date, '20260110');
  assert.equal(result.normalized[0].research_id, 'r_00001');
});

test('invalid and duplicate values block export', () => {
  for (const change of [
    { research_id: '../escape' }, { research_id: 'CON' }, { pt_id: 'a\nb' }, { data_identifier: '1e3' },
    { event_date: '04/05/2026' }, { encounter_start_date: '20260230' },
    { encounter_start_date: '20260111' },
  ]) {
    const invalid = { ...row, ...change };
    assert.ok(validate([invalid]).errors.length);
    assert.throws(() => exportCsv([invalid]));
  }
  assert.ok(validate([row, row]).errors.some(message => message.includes('重複')));
  assert.throws(() => exportCsv([row, row]));
});

test('CSV parser rejects malformed quotes and mapping duplication', () => {
  assert.throws(() => parseDelimited('a,"broken'));
  assert.throws(() => parseDelimited('a,"ok"x'));
  assert.throws(() => mappedRows([['1', '2']], [0, 0, 0, 0, 1, 1]));
});
