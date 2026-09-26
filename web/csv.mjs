export const COLUMNS = [
  'pt_id', 'research_id', 'data_identifier', 'event_date',
  'encounter_start_date', 'encounter_end_date',
];
export const REQUIRED = ['research_id', 'data_identifier', 'encounter_start_date', 'encounter_end_date'];

export function parseDelimited(text, delimiter = ',') {
  if (delimiter !== ',' && delimiter !== '\t') throw new Error('区切り文字が不正です');
  const input = text.replace(/^\uFEFF/, '');
  const rows = [];
  let row = [], cell = '', quoted = false, afterQuote = false;
  for (let i = 0; i < input.length; i++) {
    const char = input[i];
    if (quoted) {
      if (char === '"' && input[i + 1] === '"') { cell += '"'; i++; }
      else if (char === '"') { quoted = false; afterQuote = true; }
      else cell += char;
      continue;
    }
    if (afterQuote && char !== delimiter && char !== '\r' && char !== '\n') {
      throw new Error('引用符の後に不正な文字があります');
    }
    if (char === '"') {
      if (cell !== '' || afterQuote) throw new Error('引用符の位置が不正です');
      quoted = true;
    } else if (char === delimiter) {
      row.push(cell); cell = ''; afterQuote = false;
    } else if (char === '\r' || char === '\n') {
      if (char === '\r' && input[i + 1] === '\n') i++;
      row.push(cell); rows.push(row); row = []; cell = ''; afterQuote = false;
    } else {
      cell += char;
    }
  }
  if (quoted) throw new Error('閉じていない引用符があります');
  if (row.length || cell !== '' || afterQuote) { row.push(cell); rows.push(row); }
  return rows;
}

export function autoMapping(headers) {
  return COLUMNS.map(column => headers.findIndex(header => header.trim() === column));
}

export function mappedRows(rawRows, mapping) {
  if (mapping.some((source, index) =>
    ['data_identifier', 'encounter_start_date', 'encounter_end_date'].includes(COLUMNS[index]) && source < 0)) {
    throw new Error('必須列の割り当てが不足しています');
  }
  const selected = mapping.filter(source => source >= 0);
  if (new Set(selected).size !== selected.length) throw new Error('同じ入力列を複数の項目へ割り当てています');
  return rawRows.map((row, index) => {
    if (row.length !== rawRows[0].length) throw new Error(`${index + 2} 行目の列数が不正です`);
    return Object.fromEntries(COLUMNS.map((column, i) => [column, mapping[i] < 0 ? '' : row[mapping[i]].trim()]));
  });
}

export function normalizeDate(value) {
  if (value === '') return { value: '', changed: false, valid: true };
  let match = /^(\d{4})(\d{2})(\d{2})$/.exec(value);
  let changed = false;
  if (!match) {
    match = /^(\d{4})[-/](\d{2})[-/](\d{2})$/.exec(value);
    changed = !!match;
  }
  if (!match) return { value, changed: false, valid: false };
  const [, year, month, day] = match;
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  const valid = date.getUTCFullYear() === Number(year) &&
    date.getUTCMonth() + 1 === Number(month) && date.getUTCDate() === Number(day);
  return { value: `${year}${month}${day}`, changed, valid };
}

export function validate(rows) {
  const errors = [], warnings = [], information = [];
  const researchIds = new Set(), dataIds = new Set();
  let dateNormalizations = 0, idNormalizations = 0;
  const normalized = rows.map((source, index) => {
    const line = index + 1;
    const row = Object.fromEntries(COLUMNS.map(column => [column, String(source[column] ?? '').trim()]));
    for (const column of REQUIRED) if (!row[column]) errors.push(`${line} 行目: ${column} が空です`);
    if (row.research_id && (!/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(row.research_id) ||
        /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$/i.test(row.research_id)))
      errors.push(`${line} 行目: research_id は英数字・_・- の安全な名前にしてください`);
    if (COLUMNS.some(column => /[\r\n]/.test(row[column])))
      errors.push(`${line} 行目: 項目内の改行は使用できません`);
    if (row.research_id && researchIds.has(row.research_id)) errors.push(`${line} 行目: research_id が重複しています`);
    researchIds.add(row.research_id);
    if (row.data_identifier && !/^[0-9]{1,10}$/.test(row.data_identifier))
      errors.push(`${line} 行目: data_identifier は10桁以下の半角数字にしてください`);
    else if (row.data_identifier) {
      if (row.data_identifier.length < 10) { row.data_identifier = row.data_identifier.padStart(10, '0'); idNormalizations++; warnings.push(`${line} 行目: data_identifier を10桁へゼロ埋めします`); }
      if (dataIds.has(row.data_identifier)) errors.push(`${line} 行目: data_identifier が重複しています`);
      dataIds.add(row.data_identifier);
    }
    for (const column of ['event_date', 'encounter_start_date', 'encounter_end_date']) {
      const result = normalizeDate(row[column]);
      if (!result.valid || (!row[column] && column !== 'event_date')) errors.push(`${line} 行目: ${column} は有効な年月日 YYYYMMDD にしてください`);
      if (result.changed) { dateNormalizations++; warnings.push(`${line} 行目: ${column} を YYYYMMDD に変換します`); }
      row[column] = result.value;
    }
    if (row.encounter_start_date && row.encounter_end_date &&
        row.encounter_start_date > row.encounter_end_date)
      errors.push(`${line} 行目: 対象期間の開始日が終了日より後です`);
    if (row.event_date && row.encounter_start_date && row.encounter_end_date &&
        (row.event_date < row.encounter_start_date || row.event_date > row.encounter_end_date))
      warnings.push(`${line} 行目: event_date は対象期間外です`);
    for (const column of ['pt_id', 'event_date']) if (!row[column]) warnings.push(`${line} 行目: 任意項目 ${column} が空です`);
    return row;
  });
  information.push(`${rows.length} 行を編集しています`, `日付変換 ${dateNormalizations} 件`, `識別子ゼロ埋め ${idNormalizations} 件`);
  return { errors, warnings, information, normalized };
}

function escapeCsv(value) {
  const text = String(value ?? '');
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export function exportCsv(rows) {
  const result = validate(rows);
  if (result.errors.length) throw new Error('エラーを解消してから出力してください');
  const lines = [COLUMNS.join(','), ...result.normalized.map(row => COLUMNS.map(column => escapeCsv(row[column])).join(','))];
  return '\uFEFF' + lines.join('\r\n') + '\r\n';
}

export function generateResearchIds(rows, { prefix, digits, start, overwrite = false }) {
  if (!/^[A-Za-z][A-Za-z0-9_-]*$/.test(prefix) || !Number.isInteger(digits) || digits < 1 || digits > 12 ||
      !Number.isSafeInteger(start) || start < 0) throw new Error('研究 ID の生成設定が不正です');
  const existing = new Set(rows.filter(row => !overwrite && row.research_id).map(row => row.research_id));
  let next = start;
  return rows.map(row => {
    if (!overwrite && row.research_id) return { ...row };
    const value = prefix + String(next++).padStart(digits, '0');
    if (existing.has(value)) throw new Error(`生成する研究 ID ${value} が既存値と重複します`);
    existing.add(value);
    return { ...row, research_id: value };
  });
}
