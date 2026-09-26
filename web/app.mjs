import { COLUMNS, parseDelimited, autoMapping, mappedRows, validate, exportCsv, generateResearchIds } from './csv.mjs';

const emptyRow = () => Object.fromEntries(COLUMNS.map(column => [column, '']));
let rows = [emptyRow()];
let pending = null;
let activeTab = 'csv';
const byId = id => document.getElementById(id);

function showInfo(message, isError = false) {
  const target = byId('import-info');
  target.textContent = message;
  target.style.color = isError ? '#a72b2b' : '';
}

function setTab(tab) {
  activeTab = tab;
  byId('csv-panel').hidden = tab !== 'csv';
  byId('paste-panel').hidden = tab !== 'paste';
  byId('csv-tab').classList.toggle('active', tab === 'csv');
  byId('paste-tab').classList.toggle('active', tab === 'paste');
}

function renderMapping() {
  const root = byId('mapping');
  root.replaceChildren();
  byId('apply-import').disabled = !pending;
  if (!pending) {
    const note = document.createElement('p');
    note.className = 'muted';
    note.textContent = 'CSV または貼り付け内容を読み込むと、ここに列が表示されます。';
    root.append(note);
    return;
  }
  const { headers, values } = pending;
  const automatic = autoMapping(headers);
  COLUMNS.forEach((column, index) => {
    const wrapper = document.createElement('label');
    wrapper.className = 'mapping-row';
    const name = document.createElement('span');
    name.textContent = column;
    const select = document.createElement('select');
    select.dataset.target = String(index);
    const ignore = document.createElement('option');
    ignore.value = '-1'; ignore.textContent = '割り当てなし'; select.append(ignore);
    headers.forEach((header, source) => {
      const option = document.createElement('option');
      option.value = String(source);
      const preview = values[0]?.[source] ?? '';
      option.textContent = `${header}  ·  ${preview.slice(0, 16)}`;
      select.append(option);
    });
    select.value = String(automatic[index]);
    wrapper.append(name, select);
    root.append(wrapper);
  });
  showInfo(`${values.length} 行を検出しました。列を確認して取り込んでください。`);
}

function prepareImport(text, delimiter) {
  const parsed = parseDelimited(text, delimiter);
  if (!parsed.length || !parsed.some(row => row.some(cell => cell !== ''))) throw new Error('データが空です');
  const hasHeader = byId('has-header').checked;
  const headers = hasHeader ? parsed[0] : parsed[0].map((_, i) => `列${i + 1}`);
  const values = hasHeader ? parsed.slice(1) : parsed;
  if (!values.length) throw new Error('データ行がありません');
  if (headers.length !== new Set(headers).size) throw new Error('同じ見出しが複数あります');
  if (values.some(row => row.length !== headers.length)) throw new Error('行ごとの列数が一致しません');
  pending = { headers, values };
  renderMapping();
}

function renderRows() {
  const body = byId('rows');
  body.replaceChildren();
  rows.forEach((row, index) => {
    const tr = document.createElement('tr');
    const selection = document.createElement('td');
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox'; checkbox.dataset.select = String(index);
    checkbox.setAttribute('aria-label', `${index + 1} 行目を選択`);
    selection.append(checkbox); tr.append(selection);
    COLUMNS.forEach(column => {
      const td = document.createElement('td');
      const input = document.createElement('input');
      input.type = 'text'; input.value = row[column] ?? '';
      input.dataset.row = String(index); input.dataset.column = column;
      input.autocomplete = 'off'; input.spellcheck = false;
      input.setAttribute('aria-label', `${index + 1} 行目 ${column}`);
      td.append(input); tr.append(td);
    });
    body.append(tr);
  });
  byId('row-count').textContent = `${rows.length} 行`;
  renderValidation();
}

function appendMessages(parent, messages, className, limit = 8) {
  if (!messages.length) return;
  const list = document.createElement('ul');
  list.className = `message-list ${className}`;
  messages.slice(0, limit).forEach(message => {
    const item = document.createElement('li'); item.textContent = message; list.append(item);
  });
  if (messages.length > limit) {
    const item = document.createElement('li');
    item.textContent = `ほか ${messages.length - limit} 件`; list.append(item);
  }
  parent.append(list);
}

function renderValidation() {
  const result = validate(rows);
  const root = byId('validation'); root.replaceChildren();
  const headline = document.createElement('p');
  headline.className = `status ${result.errors.length ? 'error' : 'ok'}`;
  headline.textContent = `${result.errors.length} 件のエラー · ${result.warnings.length} 件の警告`;
  root.append(headline);
  appendMessages(root, result.errors, 'errors');
  appendMessages(root, result.warnings, 'warnings', 4);
  const info = document.createElement('p'); info.className = 'hint';
  info.textContent = result.information.join(' · '); root.append(info);
  byId('download').disabled = result.errors.length > 0 || rows.length === 0;
}

byId('csv-tab').addEventListener('click', () => setTab('csv'));
byId('paste-tab').addEventListener('click', () => setTab('paste'));
byId('csv-file').addEventListener('change', async event => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    if (file.size > 10_000_000) throw new Error('10 MB 以下の CSV を選択してください');
    const decoder = new TextDecoder(byId('encoding').value, { fatal: true });
    prepareImport(decoder.decode(await file.arrayBuffer()), ',');
  } catch (error) { pending = null; renderMapping(); showInfo(error.message, true); }
});
byId('parse-paste').addEventListener('click', () => {
  try { prepareImport(byId('paste-text').value, '\t'); }
  catch (error) { pending = null; renderMapping(); showInfo(error.message, true); }
});
byId('apply-import').addEventListener('click', () => {
  if (!pending) return;
  try {
    const mapping = [...byId('mapping').querySelectorAll('select')].map(select => Number(select.value));
    const incoming = mappedRows(pending.values, mapping);
    rows = rows.length === 1 && COLUMNS.every(column => !rows[0][column]) ? incoming : [...rows, ...incoming];
    pending = null; renderMapping(); renderRows();
    showInfo(`${incoming.length} 行を取り込みました。既存の行がある場合は追加しています。`);
  } catch (error) { showInfo(error.message, true); }
});
byId('rows').addEventListener('input', event => {
  const input = event.target;
  if (!input.dataset.column) return;
  rows[Number(input.dataset.row)][input.dataset.column] = input.value;
  renderValidation();
});
byId('add-row').addEventListener('click', () => { rows.push(emptyRow()); renderRows(); });
byId('delete-rows').addEventListener('click', () => {
  const selected = new Set([...byId('rows').querySelectorAll('input[data-select]:checked')].map(input => Number(input.dataset.select)));
  if (!selected.size) return;
  rows = rows.filter((_, index) => !selected.has(index));
  if (!rows.length) rows = [emptyRow()];
  renderRows();
});
byId('generate-ids').addEventListener('click', () => {
  try {
    rows = generateResearchIds(rows, {
      prefix: byId('id-prefix').value, digits: Number(byId('id-digits').value),
      start: Number(byId('id-start').value), overwrite: byId('overwrite-ids').checked,
    });
    renderRows(); showInfo('研究 ID を生成しました。');
  } catch (error) { showInfo(error.message, true); }
});
byId('download').addEventListener('click', () => {
  try {
    const csv = exportCsv(rows);
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url; link.download = 'pt_list.csv';
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30_000);
  } catch (error) { showInfo(error.message, true); }
});

renderMapping(); renderRows(); setTab(activeTab);
