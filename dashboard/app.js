import { ApiClient, SENSOR_INFO, normalizeBase, isFresh, validateAlertData, validateLimits, unwrapList, resourceMutation, csvHistory } from './core.js';

const $ = id => document.getElementById(id);
const paths = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  chart: '<path d="M4 3v17h17M7 14l4-5 4 3 6-8"/>',
  cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 3v3m6-3v3M9 18v3m6-3v3M3 9h3m-3 6h3m12-6h3m-3 6h3"/>',
  sliders: '<path d="M4 5h16M4 12h16M4 19h16"/><circle cx="8" cy="5" r="2" fill="currentColor"/><circle cx="16" cy="12" r="2" fill="currentColor"/><circle cx="10" cy="19" r="2" fill="currentColor"/>',
  layers: '<path d="m12 3 10 5-10 5L2 8zm-9 10 9 5 9-5m-18 5 9 5 9-5"/>',
  settings: '<path d="m9 3-1 3-3 1-2 3 2 2-1 3 3 2 2-1 3 2 3-2 3 1 2-3-1-3 2-2-2-3-3-1-1-3z"/><circle cx="12" cy="11" r="3"/>',
  arrow: '<path d="M4 12h15m-5-5 5 5-5 5"/>',
  refresh: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 7a7 7 0 0 1 12-1l2 3M4 15l2 3a7 7 0 0 0 12-1"/>',
  thermometer: '<path d="M9 14V5a3 3 0 0 1 6 0v9a5 5 0 1 1-6 0z"/><path d="M12 8v9"/><circle cx="12" cy="18" r="1.7" fill="currentColor"/>',
  drop: '<path d="M12 3s-7 8-7 12a7 7 0 0 0 14 0c0-4-7-12-7-12zM8 15a4 4 0 0 0 4 4"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5M17.5 17.5 19 19M5 19l1.5-1.5M17.5 6.5 19 5"/>',
  bulb: '<path d="M9 18h6m-6 3h6M8 14a7 7 0 1 1 8 0c-1 1-1 2-1 3H9c0-1 0-2-1-3zM10 10l2 2 2-2m-2 2v5"/>',
  pin: '<path d="M19 9c0 5-7 12-7 12S5 14 5 9a7 7 0 0 1 14 0z"/><circle cx="12" cy="9" r="2"/>',
  shield: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/>',
  send: '<path d="m21 3-7 18-4-7-7-4zm0 0L10 14"/>',
  activity: '<path d="M2 12h4l3-8 5 16 3-8h5"/>',
  wifi: '<path d="M3 8a14 14 0 0 1 18 0M6 12a9 9 0 0 1 12 0m-9 4a4 4 0 0 1 6 0"/><circle cx="12" cy="20" r="1" fill="currentColor"/>',
  eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>',
  plus: '<path d="M12 4v16M4 12h16"/>',
  check: '<path d="m5 12 4 4L20 5"/>',
  x: '<path d="m6 6 12 12M6 18 18 6"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/>',
  search: '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
  download: '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  warning: '<path d="m12 3 10 18H2zm0 6v5m0 3v1"/>'
};
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] ?? paths.info}</svg>`;
function icons(root = document) { root.querySelectorAll('[data-icon]').forEach(el => { el.innerHTML = icon(el.dataset.icon); }); }
const escape = input => String(input ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const format = (value, digits = 0) => Number(value).toLocaleString('pt-BR', { maximumFractionDigits: digits });
const timeFormat = new Intl.DateTimeFormat('pt-BR', { timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', second: '2-digit' });
const dateFormat = new Intl.DateTimeFormat('pt-BR', { timeZone: 'America/Sao_Paulo', dateStyle: 'short', timeStyle: 'medium' });
const time = date => Number.isFinite(Date.parse(date)) ? timeFormat.format(new Date(date)) : '—';
const dateTime = date => Number.isFinite(Date.parse(date)) ? dateFormat.format(new Date(date)) : '—';
function stored(key, fallback) { try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; } }
function saveStored(key, value) { try { localStorage.setItem(key, value); } catch { /* Navegação privada pode bloquear armazenamento. */ } }
let api = new ApiClient(stored('agnello-api', 'http://127.0.0.1:8000'));
const state = {
  page: 'visao', demo: false, alerts: null, actuator: null, limits: null,
  devices: [], resources: [], resource: 'servicos', historySensor: 'temperatura', history: [], historyLoaded: false,
  overviewSensor: 'temperatura', activities: [], monitorError: null, automation: false,
  epoch: 0, alertGeneration: 0, busyAlert: false, stoppingAlerts: false, pollTimer: null, polling: false,
  chartEpoch: { overview: 0, history: 0 }, graphURLs: {}, resourceEpoch: 0, deviceEpoch: 0, historyEpoch: 0,
  editor: null, confirmation: null, previousAlerts: null, lastChart: 0, commandVersion: 0, commandPending: false, actuatorEpoch: 0
};
let graphQueue = Promise.resolve();

function statusText(id, text, kind = '') { $(id).textContent = text; $(id).className = `helper-text ${kind}`; }
function toast(message, kind = '') {
  const box = document.createElement('div'); box.className = `toast ${kind}`;
  box.innerHTML = `${icon(kind === 'error' ? 'warning' : 'check')}<span>${escape(message)}</span><button aria-label="Dispensar aviso">×</button>`;
  box.querySelector('button').onclick = () => box.remove(); $('toasts').append(box); setTimeout(() => box.remove(), 8000);
}
function activity(text, kind = '') {
  state.activities.unshift({ text, kind, at: new Date().toISOString() }); state.activities = state.activities.slice(0, 12);
  $('activity-list').innerHTML = state.activities.map(item => `<li><span class="status-dot ${escape(item.kind)}"></span><div><strong>${escape(item.text)}</strong><small>${time(item.at)} · esta sessão</small></div></li>`).join('');
}
async function busy(button, operation) {
  button.disabled = true;
  try { return await operation(); } finally { button.disabled = false; }
}
function emptyHTML(title, description, symbol = 'chart', success = false) {
  return `<div class="empty${success ? ' success' : ''}"><span>${icon(symbol)}</span><strong>${escape(title)}</strong><p>${escape(description)}</p></div>`;
}

function initTabs(id, entries, selected, change) {
  const root = $(id);
  root.innerHTML = entries.map(([key, name, symbol]) => `<button type="button" class="tab" role="tab" data-key="${key}" aria-selected="${key === selected}" tabindex="${key === selected ? 0 : -1}">${symbol ? icon(symbol) : ''}${escape(name)}</button>`).join('');
  const select = button => {
    root.querySelectorAll('.tab').forEach(el => { el.setAttribute('aria-selected', String(el === button)); el.tabIndex = el === button ? 0 : -1; });
    change(button.dataset.key);
  };
  root.onclick = event => { const button = event.target.closest('.tab'); if (button) select(button); };
  root.onkeydown = event => {
    const buttons = [...root.querySelectorAll('.tab')], current = buttons.indexOf(document.activeElement);
    if (current < 0 || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (current + (event.key === 'ArrowRight' ? 1 : -1) + buttons.length) % buttons.length;
    buttons[next].focus(); select(buttons[next]);
  };
}
const sensorTabs = Object.entries(SENSOR_INFO).map(([key, info]) => [key, info.name.replace(' da lâmpada', ''), info.icon]);

// Exemplo é ativado pelo usuário; não substitui silenciosamente uma API offline.
const defaultLimits = {
  temperatura: { ativo: true, minimo: 10, maximo: 30 },
  umidade: { ativo: true, minimo: 50, maximo: 80 },
  luminosidade_bruta: { ativo: true, minimo: 1000, maximo: 2500 }
};
function demoAlerts() {
  const limits = state.limits ?? defaultLimits;
  const values = { temperatura: 20.4, umidade: 64.8, luminosidade_bruta: 1682 };
  const sensors = {}, alerts = [];
  for (const [key, value] of Object.entries(values)) {
    const faixa = limits[key]; const out = value < faixa.minimo || value > faixa.maximo;
    sensors[key] = { valor: value, minimo: faixa.minimo, maximo: faixa.maximo, estado: !faixa.ativo ? 'desativado' : out ? 'fora_da_faixa' : 'normal' };
    if (faixa.ativo && out) alerts.push(key === 'luminosidade_bruta' ? 'luminosidade' : key);
  }
  return { alertas: alerts, sensores: sensors, ultima_atualizacao: new Date().toISOString() };
}
function demoHistory(sensor) {
  const bases = { temperatura: 20.4, umidade: 64.8, luminosidade: 1682, brilho: 50 };
  return Array.from({ length: 30 }, (_, i) => ({ data: new Date(Date.now() - (29 - i) * 20000).toISOString(), valor: sensor === 'brilho' ? [0, 50, 100, 50][Math.floor(i / 8)] : +(bases[sensor] + Math.sin(i / 3) * bases[sensor] * .025).toFixed(sensor === 'luminosidade' ? 0 : 1) }));
}

function renderMonitor() {
  const data = state.alerts;
  const fresh = data && isFresh(data.ultima_atualizacao);
  const hasError = !!state.monitorError;
  $('connection-banner').hidden = state.demo || (!hasError && (!data || fresh));
  if (hasError) {
    $('connection-title').textContent = 'Não foi possível atualizar os sensores.';
    $('connection-description').textContent = state.monitorError;
  } else if (data && !fresh) {
    $('connection-title').textContent = 'As leituras estão sem atualização recente.';
    $('connection-description').textContent = 'Última atualização há mais de 30 segundos ou horário inválido. Confira o ESP monitor e o relógio do computador. Os comandos automáticos estão suspensos.';
  }
  const health = state.demo ? 'amber' : hasError ? 'red' : fresh ? (data.alertas.length ? 'amber' : 'green') : data ? 'amber' : '';
  $('side-dot').className = `status-dot ${health}`;
  $('side-status').textContent = state.demo ? 'Dados de exemplo' : hasError ? 'Falha na conexão' : fresh ? 'Leituras atualizadas' : data ? 'Dados sem atualização' : 'Aguardando conexão';
  $('side-description').textContent = state.demo ? 'Sem comunicação com os ESPs' : 'API local · FIWARE · MQTT';
  $('ambient-dot').className = `status-dot ${health}`;
  $('ambient-label').textContent = hasError ? 'Leituras indisponíveis' : !data ? 'Aguardando leituras' : !fresh ? 'Dados sem atualização' : data.alertas.length ? `${data.alertas.length} ${data.alertas.length === 1 ? 'sensor fora da faixa' : 'sensores fora da faixa'}` : 'Ambiente dentro dos limites';
  $('ambient-detail').textContent = hasError ? 'Confira a conexão com a API.' : !data ? 'Conecte a API para acompanhar o ambiente.' : state.demo ? 'Visualização ilustrativa.' : !fresh ? 'Valores da última leitura conhecida.' : 'Acompanhamento a cada 5 segundos.';
  $('last-reading').textContent = `Última leitura: ${data ? time(data.ultima_atualizacao) : '—'} · Brasília`;
  for (const key of ['temperatura', 'umidade', 'luminosidade_bruta']) {
    const item = data?.sensores[key]; const digits = key === 'luminosidade_bruta' ? 0 : 1;
    $(`value-${key}`).textContent = item ? format(item.valor, digits) : '—';
    const badge = $(`state-${key}`);
    badge.textContent = !item ? 'Sem leitura' : hasError || !fresh ? 'Última leitura' : item.estado === 'normal' ? 'Dentro da faixa' : item.estado === 'desativado' ? 'Alerta desativado' : 'Fora da faixa';
    badge.className = `pill ${!item ? '' : hasError || !fresh ? 'warning' : item.estado === 'normal' ? 'good' : item.estado === 'fora_da_faixa' ? 'bad' : ''}`;
    $(`range-${key}`).textContent = item ? `Faixa: ${format(item.minimo, digits)}–${format(item.maximo, digits)}${key === 'temperatura' ? ' °C' : key === 'umidade' ? '%' : ' ADC'}` : 'Faixa não carregada';
    $(`metric-${key}`).classList.toggle('alert', !!item && fresh && !hasError && item.estado === 'fora_da_faixa');
    const scale = key === 'luminosidade_bruta' ? 4095 : key === 'umidade' ? 100 : 80;
    $(`track-${key}`).style.width = item ? `${Math.max(0, Math.min(100, item.valor / scale * 100))}%` : '0%';
  }
  $('alert-count').textContent = data ? String(data.alertas.length) : '—';
  if (hasError || !fresh) $('alerts-list').innerHTML = emptyHTML(data ? 'Leituras sem atualização' : 'Aguardando leituras', 'Os valores precisam estar atualizados para o envio automático de alertas.', 'wifi');
  else if (!data.alertas.length) $('alerts-list').innerHTML = emptyHTML('Tudo dentro dos limites', 'Nenhum sensor com alerta ativo nesta leitura.', 'shield', true);
  else $('alerts-list').innerHTML = data.alertas.map(key => {
    const field = key === 'luminosidade' ? 'luminosidade_bruta' : key, item = data.sensores[field], info = SENSOR_INFO[key];
    return `<div class="alert-item"><span>${icon(info.icon)}</span><div><strong>${escape(info.name)} ${item.valor > item.maximo ? 'acima do máximo' : 'abaixo do mínimo'}</strong><p>${format(item.valor, info.decimals)} ${info.unit} · faixa ${format(item.minimo, info.decimals)}–${format(item.maximo, info.decimals)} ${info.unit}</p></div></div>`;
  }).join('');
  if (data && fresh && !hasError) {
    const signature = JSON.stringify(data.alertas);
    if (state.previousAlerts !== signature) {
      if (state.previousAlerts !== null || data.alertas.length) activity(data.alertas.length ? `Fora da faixa: ${data.alertas.map(key => SENSOR_INFO[key].name).join(', ')}.` : 'Todos os sensores voltaram à faixa configurada.', data.alertas.length ? 'amber' : 'green');
      state.previousAlerts = signature;
    }
  }
  renderAutomation();
}

function renderActuator() {
  const current = state.actuator;
  const fresh = current && isFresh(current.recebido_em);
  $('value-brilho').textContent = current ? format(current.brilho) : '—';
  $('track-brilho').style.width = current ? `${current.brilho}%` : '0%';
  $('state-brilho').textContent = !current ? 'Sem confirmação' : !fresh ? 'Última confirmação' : state.demo ? 'Exemplo' : 'ESP respondeu';
  $('state-brilho').className = `pill ${fresh ? 'good' : 'warning'}`;
  $('control-mode').textContent = !current ? 'Modo não consultado' : `${current.modo === 'automatico' ? 'Automático' : 'Manual'}${fresh ? '' : ' · última resposta'}`;
  $('mode-auto').classList.toggle('selected', fresh && current.modo === 'automatico');
  $('mode-manual').classList.toggle('selected', fresh && current.modo === 'manual');
  $('light-description').textContent = !fresh ? 'Consulte o atuador para confirmar o modo e o brilho.' : current.modo === 'automatico' ? 'O ESP monitor define o brilho: 0%, 50% ou 100%, conforme o LDR.' : 'A intensidade é definida por você. O atuador ignora os comandos automáticos do monitor.';
  $('lamp-art').style.color = current?.brilho ? '#b39556' : '#b1a7ad';
  $('lamp-art').style.background = current?.brilho ? `radial-gradient(ellipse at center,rgba(227,195,122,${current.brilho / 200}),transparent 72%)` : 'none';
}

function renderAutomation() {
  $('toggle-alerts').setAttribute('aria-checked', String(state.automation));
  $('toggle-alerts').disabled = state.stoppingAlerts;
  if (state.demo) statusText('automation-status', 'Exemplo: a automação real está indisponível neste modo.');
  else if (state.stoppingAlerts) statusText('automation-status', 'Enviando comando para encerrar os alertas…');
  else if (!state.automation) statusText('automation-status', 'Desativado. Ative para acompanhar as leituras e enviar os alertas.');
  else if (state.monitorError || !state.alerts || !isFresh(state.alerts.ultima_atualizacao)) statusText('automation-status', 'Ativado, mas aguardando leituras recentes. Um alerta já recebido pelo ESP pode continuar tocando.', 'error');
}

// Só uma publicação por vez. A lista também é reenviada quando vazia,
// permitindo encerrar alertas e restabelecer o estado após reconexões do ESP.
async function syncAlerts() {
  if (state.demo || !state.automation || state.busyAlert || state.monitorError || !state.alerts || !isFresh(state.alerts.ultima_atualizacao)) return;
  const epoch = state.epoch, generation = state.alertGeneration;
  state.busyAlert = true;
  try {
    await api.request('/monitor/alertas', { method: 'POST', body: { alertas: state.alerts.alertas } });
    if (epoch !== state.epoch || generation !== state.alertGeneration) return;
    statusText('automation-status', state.alerts.alertas.length ? 'Comando de alerta aceito pelo MQTT. Confira o LED e o buzzer no ESP.' : 'Comando para encerrar alertas aceito pelo MQTT.', 'success');
  } catch (error) {
    if (epoch === state.epoch && generation === state.alertGeneration) statusText('automation-status', `Falha no envio: ${error.message}`, 'error');
  } finally { state.busyAlert = false; }
}

async function toggleAlerts() {
  if (state.demo) return toast('Saia da visualização de exemplo para controlar o ESP.', 'error');
  if (state.automation) {
    // Aguarda qualquer envio em andamento antes do comando vazio: evita
    // que um alerta antigo seja publicado depois do encerramento.
    state.automation = false; state.alertGeneration++; state.stoppingAlerts = true; renderAutomation();
    const epoch = state.epoch;
    while (state.busyAlert) await new Promise(resolve => setTimeout(resolve, 50));
    try {
      if (epoch !== state.epoch) return;
      await api.request('/monitor/alertas', { method: 'POST', body: { alertas: [] } });
      if (epoch !== state.epoch) return;
      statusText('automation-status', 'Automação desativada. Comando para encerrar alertas aceito pelo MQTT.', 'success');
      activity('Automação de alertas desativada; encerramento enviado.', 'green');
    } catch (error) {
      if (epoch !== state.epoch) return;
      statusText('automation-status', `Automação desativada, mas o encerramento falhou: ${error.message}. O ESP pode continuar tocando.`, 'error');
      toast('Não foi possível enviar o encerramento dos alertas.', 'error');
    } finally { state.stoppingAlerts = false; $('toggle-alerts').disabled = false; }
  } else {
    state.automation = true; state.alertGeneration++; renderAutomation();
    activity('Automação de alertas ativada nesta dashboard.', 'green');
    await poll();
  }
}

async function queryActuator({ silent = false } = {}) {
  const epoch = state.epoch, version = state.commandVersion, token = ++state.actuatorEpoch;
  try {
    const data = state.demo ? { modo: 'automatico', brilho: 50, recebido_em: new Date().toISOString() } : await api.request('/atuador/estado', { timeout: 10000 });
    if (epoch !== state.epoch || version !== state.commandVersion || token !== state.actuatorEpoch) return;
    if (!['manual', 'automatico'].includes(data.modo) || !Number.isInteger(data.brilho) || data.brilho < 0 || data.brilho > 100) throw new Error('Resposta inesperada do atuador.');
    state.actuator = data; renderActuator();
    if (!silent) { activity(`ESP atuador respondeu: ${data.modo === 'manual' ? 'manual' : 'automático'}, brilho ${data.brilho}%.`, 'green'); toast('Estado recebido do ESP atuador.', 'good'); }
    return data;
  } catch (error) {
    if (epoch !== state.epoch || version !== state.commandVersion || token !== state.actuatorEpoch) return;
    renderActuator();
    if (!silent) toast(error.message, 'error');
  }
}

async function lampCommand(mode) {
  if (state.demo) return toast('Os controles reais estão desativados na visualização de exemplo.', 'error');
  if (state.commandPending) return;
  state.commandPending = true; state.commandVersion++;
  const epoch = state.epoch;
  const brightness = Number($('brightness').value);
  const buttons = [$('mode-auto'), $('mode-manual'), $('apply-brightness')]; buttons.forEach(b => b.disabled = true);
  try {
    await api.request(`/atuador/${mode === 'manual' ? 'manual' : 'automatico'}`, { method: 'POST', ...(mode === 'manual' ? { body: { brilho: brightness } } : {}) });
    if (epoch !== state.epoch) return;
    statusText('command-status', 'Comando aceito pelo MQTT. Aguardando resposta do atuador…');
    activity(mode === 'manual' ? `Solicitado modo manual com brilho de ${brightness}%.` : 'Solicitado modo automático da lâmpada.');
    const result = await queryActuator({ silent: true });
    if (epoch !== state.epoch) return;
    if (result?.modo === mode && (mode !== 'manual' || result.brilho === brightness)) {
      statusText('command-status', `ESP respondeu: ${mode === 'manual' ? 'manual' : 'automático'}, brilho ${result.brilho}%.`, 'success');
      toast('Estado do atuador confirmado por uma resposta do ESP.', 'good');
    } else {
      statusText('command-status', 'O MQTT aceitou o comando, mas o estado solicitado ainda não foi confirmado. Use “Consultar ESP”.', 'error');
    }
  } catch (error) { if (epoch === state.epoch) { statusText('command-status', error.message, 'error'); toast(error.message, 'error'); } }
  finally { state.commandPending = false; buttons.forEach(b => b.disabled = false); }
}

async function poll() {
  clearTimeout(state.pollTimer);
  if (state.polling) return;
  state.polling = true;
  const epoch = state.epoch;
  try {
    if (state.demo) {
      state.alerts = demoAlerts(); state.monitorError = null;
      state.actuator = { modo: 'automatico', brilho: 50, recebido_em: new Date().toISOString() };
    } else {
      const data = await api.request('/alertas');
      if (epoch !== state.epoch) return;
      state.alerts = validateAlertData(data); state.monitorError = null;
    }
    if (epoch !== state.epoch) return;
    renderMonitor(); renderActuator();
    // Renderização Matplotlib sequencial; só recarrega o gráfico visível.
    if (state.page === 'visao' && Date.now() - state.lastChart > 30000) {
      state.lastChart = Date.now(); void loadChart('overview', state.overviewSensor);
    }
    await syncAlerts();
  } catch (error) {
    if (epoch === state.epoch) { state.monitorError = error.message; renderMonitor(); }
  } finally {
    state.polling = false;
    state.pollTimer = setTimeout(poll, epoch === state.epoch ? 5000 : 0);
  }
}

function illustrativeChart(sensor) {
  const rows = demoHistory(sensor), values = rows.map(r => r.valor), low = Math.min(...values), high = Math.max(...values);
  const scale = high - low || 1;
  const points = values.map((value, i) => `${50 + i * 19.3},${205 - (value - low) / scale * 130}`).join(' ');
  const lines = [55, 105, 155, 205].map(y => `<line x1="50" y1="${y}" x2="625" y2="${y}" stroke="#eee7ec" stroke-dasharray="3 4"/>`).join('');
  return `<svg class="demo-chart" viewBox="0 0 670 265" role="img" aria-label="Gráfico ilustrativo de ${escape(SENSOR_INFO[sensor].name)}"><text x="50" y="23" font-family="Segoe UI,Arial" font-size="10" fill="#968490">DADOS ILUSTRATIVOS · NÃO É UM GRÁFICO DA API</text>${lines}<polyline points="${points}" fill="none" stroke="#58273d" stroke-width="2.5" stroke-linejoin="round"/><text x="50" y="245" font-family="Segoe UI,Arial" font-size="10" fill="#968490">${time(rows[0].data)}</text><text x="560" y="245" font-family="Segoe UI,Arial" font-size="10" fill="#968490">${time(rows.at(-1).data)}</text><text x="15" y="62" font-family="Segoe UI,Arial" font-size="10" fill="#968490">${format(high, 1)}</text><text x="15" y="207" font-family="Segoe UI,Arial" font-size="10" fill="#968490">${format(low, 1)}</text></svg>`;
}
function releaseGraph(kind) { if (state.graphURLs[kind]) { URL.revokeObjectURL(state.graphURLs[kind]); delete state.graphURLs[kind]; } }
async function loadChart(kind, sensor) {
  const target = $(`${kind}-chart`), token = ++state.chartEpoch[kind], epoch = state.epoch;
  target.innerHTML = '<p class="loading">Carregando gráfico…</p>';
  if (state.demo) { releaseGraph(kind); target.innerHTML = illustrativeChart(sensor); return; }
  try {
    // Matplotlib no backend é compartilhado: esta dashboard não inicia
    // duas renderizações de gráfico ao mesmo tempo.
    const source = api;
    const task = graphQueue.catch(() => {}).then(() => {
      if (token !== state.chartEpoch[kind] || epoch !== state.epoch) throw new Error('Consulta substituída.');
      return source.request(`/graficos/${sensor}`, { blob: true, timeout: 20000 });
    });
    graphQueue = task;
    const blob = await task;
    if (token !== state.chartEpoch[kind] || epoch !== state.epoch) return;
    if (!blob.type.startsWith('image/')) throw new Error('A API não retornou uma imagem para o gráfico.');
    releaseGraph(kind); const url = URL.createObjectURL(blob); state.graphURLs[kind] = url;
    const image = new Image(); image.alt = `Histórico de ${SENSOR_INFO[sensor].name}, gerado com Matplotlib a partir do STH-Comet.`;
    image.onerror = () => { if (token === state.chartEpoch[kind]) target.innerHTML = emptyHTML('Não foi possível exibir o gráfico', 'A imagem recebida não pôde ser decodificada.'); };
    image.src = url; target.replaceChildren(image);
  } catch (error) {
    if (token === state.chartEpoch[kind] && epoch === state.epoch) { releaseGraph(kind); target.innerHTML = emptyHTML('Gráfico indisponível', error.message); }
  }
}

async function loadHistory() {
  const sensor = state.historySensor, token = ++state.historyEpoch, epoch = state.epoch;
  state.historyLoaded = false; state.history = [];
  $('download-csv').disabled = true; $('download-png').disabled = true;
  $('history-title').textContent = SENSOR_INFO[sensor].name;
  $('history-unit').textContent = `VALOR (${SENSOR_INFO[sensor].unit})`;
  $('history-table').innerHTML = '<tr><td class="table-empty" colspan="3">Consultando o histórico…</td></tr>';
  const graph = loadChart('history', sensor);
  try {
    const rows = state.demo ? demoHistory(sensor) : await api.request(`/historico/${sensor}`);
    if (epoch !== state.epoch || token !== state.historyEpoch) return;
    if (!Array.isArray(rows)) throw new Error('Formato de histórico inesperado.');
    state.history = rows; state.historyLoaded = true;
    $('history-table').innerHTML = rows.length ? rows.map((row, i) => `<tr><td><span class="sensor-key">${String(i + 1).padStart(2, '0')}</span></td><td>${dateTime(row.data)}</td><td><strong>${escape(format(row.valor, SENSOR_INFO[sensor].decimals))}</strong> ${SENSOR_INFO[sensor].unit}</td></tr>`).join('') : '<tr><td class="table-empty" colspan="3">Ainda não há registros para este sensor.</td></tr>';
    $('history-count').textContent = `${rows.length} registros${state.demo ? ' ilustrativos' : ' carregados'}`;
    $('download-csv').disabled = !rows.length || state.demo;
  } catch (error) {
    if (epoch === state.epoch && token === state.historyEpoch) { $('history-table').innerHTML = `<tr><td class="table-empty" colspan="3">${escape(error.message)}</td></tr>`; $('history-count').textContent = 'Histórico indisponível'; }
  }
  await graph;
  if (epoch === state.epoch && token === state.historyEpoch) $('download-png').disabled = state.demo || !state.graphURLs.history;
}
function download(blob, filename) {
  const url = URL.createObjectURL(blob), anchor = document.createElement('a'); anchor.href = url; anchor.download = filename;
  document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function renderLimits() {
  const definitions = [
    ['temperatura', 'Temperatura', 'thermometer', '°C', 'Temperatura do ambiente medida pelo DHT.'],
    ['umidade', 'Umidade', 'drop', '%', 'Umidade relativa do ambiente medida pelo DHT.'],
    ['luminosidade_bruta', 'Luminosidade', 'sun', 'ADC', 'Leitura bruta do LDR. Quanto maior, menos luz na montagem atual.']
  ];
  $('limit-fields').innerHTML = definitions.map(([key, name, symbol, unit, description]) => `<article class="limit-card"><div class="limit-card-head"><div><span class="metric-icon ${key === 'temperatura' ? 'wine' : key === 'umidade' ? 'blue' : 'amber'}">${icon(symbol)}</span><h3>${name}</h3></div><span class="pill">${unit}</span></div><p>${description}</p><div class="form-grid"><label class="field">Mínimo (${unit})<input id="limit-min-${key}" type="number" step="${key === 'luminosidade_bruta' ? '1' : 'any'}" ${key !== 'temperatura' ? `min="0" max="${key === 'umidade' ? 100 : 4095}"` : ''} required></label><label class="field">Máximo (${unit})<input id="limit-max-${key}" type="number" step="${key === 'luminosidade_bruta' ? '1' : 'any'}" ${key !== 'temperatura' ? `min="0" max="${key === 'umidade' ? 100 : 4095}"` : ''} required></label></div><label class="checkbox-row"><input id="limit-active-${key}" type="checkbox"><span>Habilitar alerta deste sensor</span></label></article>`).join('');
  fillLimits();
}
function fillLimits() {
  for (const key of ['temperatura', 'umidade', 'luminosidade_bruta']) {
    const item = state.limits?.[key];
    $(`limit-min-${key}`).value = item?.minimo ?? '';
    $(`limit-max-${key}`).value = item?.maximo ?? '';
    $(`limit-active-${key}`).checked = item?.ativo ?? false;
  }
  $('save-limits').disabled = !state.limits;
}
async function loadLimits() {
  const epoch = state.epoch;
  statusText('limits-status', 'Carregando limites…');
  try {
    const data = state.demo ? structuredClone(defaultLimits) : await api.request('/limites');
    if (epoch !== state.epoch) return;
    state.limits = validateLimits(data); fillLimits();
    statusText('limits-status', state.demo ? 'Configuração ilustrativa. A gravação real está desativada.' : 'Configuração carregada da API.', 'success');
  } catch (error) { if (epoch === state.epoch) { state.limits = null; fillLimits(); statusText('limits-status', error.message, 'error'); } }
}
async function saveLimits(event) {
  event.preventDefault();
  if (state.demo) return toast('Saia do modo de exemplo para salvar limites reais.', 'error');
  const epoch = state.epoch;
  await busy($('save-limits'), async () => {
    try {
      const data = {};
      for (const key of ['temperatura', 'umidade', 'luminosidade_bruta']) data[key] = { ativo: $(`limit-active-${key}`).checked, minimo: Number($(`limit-min-${key}`).value), maximo: Number($(`limit-max-${key}`).value) };
      validateLimits(data);
      await api.request('/limites', { method: 'PUT', body: data });
      if (epoch !== state.epoch) return;
      state.limits = data; statusText('limits-status', 'Limites salvos pela API no limites.json.', 'success');
      toast('Limites atualizados.', 'good'); activity('Limites dos sensores atualizados.', 'green'); void poll();
    } catch (error) { if (epoch === state.epoch) statusText('limits-status', error.message, 'error'); }
  });
}

function demoDevices() { return [
  { device_id: 'monitor001', entity_name: 'urn:ngsi-ld:Environment:001', entity_type: 'Environment', protocol: 'PDI-IoTA-UltraLight', transport: 'MQTT', attributes: [{ object_id: 't', name: 'temperature', type: 'Number' }, { object_id: 'h', name: 'humidity', type: 'Number' }, { object_id: 'l', name: 'luminosityRaw', type: 'Integer' }], static_attributes: [{ name: 'local', type: 'Text', value: 'Bancada CP5' }] },
  { device_id: 'atuador001', entity_name: 'urn:ngsi-ld:Actuator:001', entity_type: 'Actuator', protocol: 'PDI-IoTA-UltraLight', transport: 'MQTT', attributes: [{ object_id: 'b', name: 'brightness', type: 'Integer' }] }
]; }
async function loadDevices() {
  const token = ++state.deviceEpoch, epoch = state.epoch;
  $('device-table').innerHTML = '<tr><td class="table-empty" colspan="6">Consultando dispositivos…</td></tr>';
  try {
    const rows = state.demo ? demoDevices() : unwrapList(await api.request('/dispositivos'), 'dispositivos');
    if (epoch !== state.epoch || token !== state.deviceEpoch) return;
    state.devices = rows; renderDevices();
  } catch (error) { if (epoch === state.epoch && token === state.deviceEpoch) { state.devices = []; $('device-table').innerHTML = `<tr><td class="table-empty" colspan="6">${escape(error.message)}</td></tr>`; $('device-count').textContent = 'Consulta indisponível'; } }
}
function actionButtons(index, editable = true) { return `<div class="row-actions"><button type="button" data-action="view" data-index="${index}">Detalhes</button>${editable ? `<button type="button" data-action="edit" data-index="${index}">Editar</button>` : ''}<button type="button" class="delete" data-action="delete" data-index="${index}">Excluir</button></div>`; }
function renderDevices() {
  const query = $('device-search').value.toLowerCase();
  const rows = state.devices.map((item, index) => ({ item, index })).filter(({ item }) => `${item.device_id} ${item.entity_name}`.toLowerCase().includes(query));
  $('device-table').innerHTML = rows.length ? rows.map(({ item, index }) => `<tr><td><strong>${escape(item.device_id)}</strong><small>${escape(item.protocol ?? 'Protocolo não informado')}</small></td><td><span class="sensor-key">${escape(item.entity_name)}</span></td><td>${escape(item.entity_type)}</td><td><span class="pill">${escape(item.transport ?? '—')}</span></td><td>${Array.isArray(item.attributes) ? item.attributes.length : 0}</td><td>${actionButtons(index)}</td></tr>`).join('') : '<tr><td class="table-empty" colspan="6">Nenhum dispositivo encontrado.</td></tr>';
  $('device-count').textContent = `${rows.length} de ${state.devices.length} dispositivos${state.demo ? ' ilustrativos' : ''}`;
}
function devicePreset() {
  const profile = $('device-profile').value;
  if (profile === 'custom') return;
  $('device-type').value = profile === 'monitor' ? 'Environment' : 'Actuator';
  $('device-attributes').value = JSON.stringify(demoDevices()[profile === 'monitor' ? 0 : 1].attributes, null, 2);
}
async function createDevice(event) {
  event.preventDefault();
  if (state.demo) return toast('Cadastros reais estão desativados no modo de exemplo.', 'error');
  const epoch = state.epoch;
  await busy(event.submitter, async () => {
    try {
      const attributes = JSON.parse($('device-attributes').value);
      if (!Array.isArray(attributes) || attributes.some(x => !x.object_id || !x.name || !x.type)) throw new Error('Os atributos devem ser uma lista com object_id, name e type.');
      const location = $('device-location').value.trim();
      const device = {
        device_id: $('device-id').value.trim(), entity_name: $('device-entity').value.trim(), entity_type: $('device-type').value.trim(),
        protocol: $('device-protocol').value.trim(), transport: $('device-transport').value, attributes,
        ...(location ? { static_attributes: [{ name: 'local', type: 'Text', value: location }] } : {})
      };
      await api.request('/dispositivos', { method: 'POST', body: { devices: [device] } });
      if (epoch !== state.epoch) return;
      $('device-dialog').close(); toast('Dispositivo cadastrado no IoT Agent.', 'good'); activity(`Dispositivo ${device.device_id} cadastrado.`, 'green'); await loadDevices();
    } catch (error) { if (epoch === state.epoch) statusText('device-form-status', error.message, 'error'); }
  });
}

const resourceConfig = {
  servicos: { title: 'Serviços', singular: 'serviço', description: 'Grupos de provisionamento e conexão do IoT Agent.', fields: [['apikey', 'CHAVE DO SERVIÇO'], ['resource', 'RECURSO'], ['entity_type', 'TIPO DE ENTIDADE'], ['cbroker', 'CONTEXT BROKER']], template: { services: [{ apikey: 'CP5NOVO', cbroker: 'http://orion:1026', entity_type: 'Thing', resource: '' }] }, editDescription: 'Informe somente os campos do serviço a atualizar. A chave e o recurso selecionam o serviço e não são alterados por este formulário.' },
  entidades: { title: 'Entidades', singular: 'entidade', description: 'Dados de contexto armazenados no Orion Context Broker.', fields: [['id', 'IDENTIFICADOR'], ['type', 'TIPO'], ['TimeInstant', 'ÚLTIMA ATUALIZAÇÃO']], template: { id: 'urn:ngsi-ld:Environment:002', type: 'Environment', local: { type: 'Text', value: 'Bancada CP5' } }, editDescription: 'Edite apenas os atributos da entidade, no formato NGSI v2. ID e tipo não fazem parte desta atualização.' },
  assinaturas: { title: 'Assinaturas', singular: 'assinatura', description: 'Notificações do Orion para o histórico ou outros consumidores.', fields: [['id', 'IDENTIFICADOR'], ['description', 'DESCRIÇÃO'], ['status', 'ESTADO']], template: { description: 'Histórico do monitor002', subject: { entities: [{ id: 'urn:ngsi-ld:Environment:002', type: 'Environment' }], condition: { attrs: ['temperature', 'humidity', 'luminosityRaw'] } }, notification: { http: { url: 'http://sth-comet:8666/notify' }, attrs: ['temperature', 'humidity', 'luminosityRaw'], attrsFormat: 'legacy', metadata: ['TimeInstant'] } }, editDescription: 'Atualize os campos da assinatura. Confira o consumidor de notificações antes de salvar.' },
  registros: { title: 'Registros', singular: 'registro', description: 'Provedores de contexto cadastrados no Orion.', fields: [['id', 'IDENTIFICADOR'], ['description', 'DESCRIÇÃO'], ['status', 'ESTADO']], template: { description: 'Provedor de contexto CP5', dataProvided: { entities: [{ id: 'urn:ngsi-ld:Environment:002', type: 'Environment' }], attrs: ['temperature'] }, provider: { http: { url: 'http://iot-agent:4041' }, legacyForwarding: false } }, editDescription: '' }
};
function demoResources(resource) {
  if (resource === 'servicos') return [{ apikey: 'TEF', resource: '', entity_type: 'Thing', cbroker: 'http://orion:1026' }];
  if (resource === 'entidades') return [{ id: 'urn:ngsi-ld:Environment:001', type: 'Environment', temperature: { type: 'Number', value: 20.4 }, humidity: { type: 'Number', value: 64.8 }, luminosityRaw: { type: 'Integer', value: 1682 }, TimeInstant: { type: 'DateTime', value: new Date().toISOString() } }];
  return [{ id: 'exemplo-sem-id-real', description: resource === 'assinaturas' ? 'Histórico do monitor · exemplo' : 'Provedor de contexto · exemplo', status: 'active' }];
}
async function loadResource() {
  const resource = state.resource, config = resourceConfig[resource], token = ++state.resourceEpoch, epoch = state.epoch;
  $('resource-title').textContent = config.title; $('resource-description').textContent = config.description;
  $('new-resource').innerHTML = `${icon('plus')}Novo ${config.singular}`;
  $('resource-head').innerHTML = `<tr>${config.fields.map(([, label]) => `<th>${label}</th>`).join('')}<th>AÇÕES</th></tr>`;
  $('resource-table').innerHTML = `<tr><td colspan="${config.fields.length + 1}" class="table-empty">Consultando ${config.title.toLowerCase()}…</td></tr>`;
  try {
    const rows = state.demo ? demoResources(resource) : unwrapList(await api.request(`/${resource}`), resource);
    if (token !== state.resourceEpoch || epoch !== state.epoch) return;
    state.resources = rows;
    $('resource-count').textContent = `${rows.length} ${rows.length === 1 ? 'item' : 'itens'}`;
    $('resource-table').innerHTML = rows.length ? rows.map((item, index) => `<tr>${config.fields.map(([field]) => {
      const value = field === 'TimeInstant' ? dateTime(item[field]?.value) : item[field] === '' ? '(vazio)' : item[field] ?? '—';
      return `<td>${field === 'id' ? `<span class="sensor-key">${escape(value)}</span>` : escape(value)}</td>`;
    }).join('')}<td>${actionButtons(index, resource !== 'registros')}</td></tr>`).join('') : `<tr><td class="table-empty" colspan="${config.fields.length + 1}">Nenhum item cadastrado.</td></tr>`;
  } catch (error) { if (token === state.resourceEpoch && epoch === state.epoch) { state.resources = []; $('resource-count').textContent = 'Indisponível'; $('resource-table').innerHTML = `<tr><td class="table-empty" colspan="${config.fields.length + 1}">${escape(error.message)}</td></tr>`; } }
}
function editablePayload(resource, item) {
  if (resource === 'dispositivos') return { attributes: item.attributes ?? [], static_attributes: item.static_attributes ?? [] };
  if (resource === 'servicos') { const { apikey, resource: ignored, ...rest } = item; return rest; }
  if (resource === 'entidades') { const { id, type, ...attrs } = item; return attrs; }
  if (resource === 'assinaturas') { const { id, status, ...rest } = item; if (status === 'active' || status === 'inactive') rest.status = status; if (rest.notification) { rest.notification = { ...rest.notification }; for (const key of ['timesSent', 'lastNotification', 'lastSuccess', 'lastSuccessCode', 'lastFailure', 'lastFailureReason']) delete rest.notification[key]; } return rest; }
  return item;
}
function openEditor(resource, action, item = {}) {
  const config = resource === 'dispositivos' ? { title: 'Dispositivo', singular: 'dispositivo', editDescription: 'A API atual atualiza atributos e atributos estáticos. Alterar os GPIOs exige modificar o firmware no Wokwi ou ESP físico.' } : resourceConfig[resource];
  state.editor = { resource, action, item, epoch: state.epoch };
  $('editor-title').textContent = action === 'view' ? `Detalhes do ${config.singular}` : action === 'create' ? `Cadastrar ${config.singular}` : `Editar ${config.singular}`;
  $('editor-description').textContent = action === 'view' ? 'Configuração retornada pela API. Use a opção Editar para aplicar alterações.' : action === 'create' ? 'Adapte a configuração ao seu dispositivo e ambiente. O modelo é um ponto de partida para o cadastro.' : config.editDescription;
  $('editor-json').value = JSON.stringify(action === 'view' ? item : action === 'create' ? config.template : editablePayload(resource, item), null, 2);
  $('editor-json').readOnly = action === 'view'; $('editor-submit').hidden = action === 'view';
  statusText('editor-status', ''); $('editor-dialog').showModal();
}
async function saveEditor(event) {
  event.preventDefault();
  if (state.demo) return toast('Alterações reais estão desativadas no modo de exemplo.', 'error');
  const editor = state.editor;
  if (!editor || editor.action === 'view' || editor.epoch !== state.epoch) return;
  await busy($('editor-submit'), async () => {
    try {
      const body = JSON.parse($('editor-json').value);
      if (!body || Array.isArray(body) || typeof body !== 'object') throw new Error('Use um objeto JSON válido para a configuração.');
      const route = resourceMutation(editor.resource, editor.action, editor.item);
      await api.request(route.path, { method: route.method, body });
      if (editor.epoch !== state.epoch) return;
      $('editor-dialog').close(); toast('Configuração salva pela API.', 'good'); activity(`Configuração de ${editor.resource} atualizada.`, 'green');
      await (editor.resource === 'dispositivos' ? loadDevices() : loadResource());
    } catch (error) { if (editor.epoch === state.epoch) statusText('editor-status', error.message, 'error'); }
  });
}
function confirmDelete(resource, item) {
  const name = item.device_id ?? item.id ?? `chave ${item.apikey}, recurso ${item.resource || '(vazio)'}`;
  state.confirmation = { resource, item, name, epoch: state.epoch };
  $('confirm-title').textContent = 'Excluir este item?';
  $('confirm-description').textContent = `Você está excluindo “${name}” do servidor FIWARE. Isso pode interromper o monitoramento ou o histórico que depende desse cadastro.`;
  statusText('confirm-status', ''); $('confirm-dialog').showModal();
}
async function deleteConfirmed() {
  if (state.demo) return toast('Exclusões reais estão desativadas no modo de exemplo.', 'error');
  const confirmation = state.confirmation;
  if (!confirmation || confirmation.epoch !== state.epoch) return;
  await busy($('confirm-delete'), async () => {
    try {
      const route = resourceMutation(confirmation.resource, 'delete', confirmation.item);
      await api.request(route.path, { method: route.method });
      if (confirmation.epoch !== state.epoch) return;
      $('confirm-dialog').close(); toast('Item excluído do FIWARE.', 'good'); activity(`Excluído: ${confirmation.name}.`, 'amber');
      await (confirmation.resource === 'dispositivos' ? loadDevices() : loadResource());
    } catch (error) { if (confirmation.epoch === state.epoch) statusText('confirm-status', error.message, 'error'); }
  });
}
function handleRowAction(event, resource, rows) {
  const button = event.target.closest('button[data-action]'); if (!button) return;
  const item = rows[Number(button.dataset.index)]; if (!item) return;
  if (button.dataset.action === 'delete') confirmDelete(resource, item); else openEditor(resource, button.dataset.action, item);
}

function showPage() {
  const key = location.hash.slice(1), allowed = ['visao', 'historico', 'dispositivos', 'limites', 'fiware'];
  state.page = allowed.includes(key) ? key : 'visao';
  document.querySelectorAll('.page').forEach(el => { el.hidden = el.id !== `page-${state.page}`; });
  document.querySelectorAll('.nav-item').forEach(el => { el.classList.toggle('active', el.dataset.page === state.page); if (el.dataset.page === state.page) el.setAttribute('aria-current', 'page'); else el.removeAttribute('aria-current'); });
  $('breadcrumb-page').textContent = { visao: 'Visão geral', historico: 'Histórico & gráficos', dispositivos: 'Dispositivos', limites: 'Limites & alertas', fiware: 'Gerenciamento FIWARE' }[state.page];
  document.title = `${$('breadcrumb-page').textContent} · Agnello`;
  if (state.page === 'historico') void loadHistory();
  if (state.page === 'dispositivos') void loadDevices();
  if (state.page === 'limites') void loadLimits();
  if (state.page === 'fiware') void loadResource();
}

function openSettings() { $('api-url').value = api.base; $('demo-option').checked = state.demo; $('settings-dialog').showModal(); }
async function changeConnection(base, demo) {
  if (state.automation || state.busyAlert || state.stoppingAlerts) throw new Error('Desative os alertas automáticos na visão geral antes de trocar a conexão.');
  state.epoch++; state.alertGeneration++; state.commandVersion++;
  api = new ApiClient(base); saveStored('agnello-api', api.base);
  state.demo = demo; state.alerts = null; state.actuator = null; state.limits = null; state.monitorError = null;
  state.previousAlerts = null; state.lastChart = 0; state.devices = []; state.resources = []; state.history = []; state.historyLoaded = false;
  state.chartEpoch.overview++; state.chartEpoch.history++;
  releaseGraph('overview'); releaseGraph('history');
  $('demo-banner').hidden = !demo; $('chart-source').textContent = demo ? 'Gráfico ilustrativo · dados de exemplo' : 'Histórico via STH-Comet · gráfico Matplotlib';
  statusText('command-status', 'Nenhum comando enviado nesta conexão.');
  renderMonitor(); renderActuator(); fillLimits();
  activity(demo ? 'Visualização de exemplo ativada. Nenhum comando real será enviado.' : `Conexão configurada: ${api.base}.`, demo ? 'amber' : '');
  showPage(); await poll(); void queryActuator({ silent: true });
}

icons(); renderLimits();
initTabs('overview-chart-tabs', sensorTabs, state.overviewSensor, sensor => { state.overviewSensor = sensor; void loadChart('overview', sensor); });
initTabs('history-tabs', sensorTabs, state.historySensor, sensor => { state.historySensor = sensor; void loadHistory(); });
initTabs('resource-tabs', Object.entries(resourceConfig).map(([key, config]) => [key, config.title, 'layers']), state.resource, resource => { state.resource = resource; void loadResource(); });
$('brightness').oninput = () => { $('brightness-label').textContent = `${$('brightness').value}%`; };
$('mode-auto').onclick = () => lampCommand('automatico');
$('mode-manual').onclick = () => lampCommand('manual');
$('apply-brightness').onclick = () => lampCommand('manual');
$('query-actuator').onclick = () => busy($('query-actuator'), () => queryActuator());
$('toggle-alerts').onclick = toggleAlerts;
$('refresh').onclick = () => busy($('refresh'), async () => { await poll(); await queryActuator({ silent: true }); if (state.page === 'historico') await loadHistory(); if (state.page === 'dispositivos') await loadDevices(); if (state.page === 'fiware') await loadResource(); });
$('reload-history').onclick = () => busy($('reload-history'), loadHistory);
$('download-csv').onclick = () => { if (!state.demo && state.historyLoaded && state.history.length) download(new Blob([csvHistory(state.history)], { type: 'text/csv;charset=utf-8' }), `agnello-${state.historySensor}.csv`); };
$('download-png').onclick = async () => { if (state.demo || !state.graphURLs.history) return; const blob = await fetch(state.graphURLs.history).then(res => res.blob()); download(blob, `agnello-${state.historySensor}.png`); };
$('reload-devices').onclick = () => busy($('reload-devices'), loadDevices);
$('device-search').oninput = renderDevices;
$('new-device').onclick = () => { $('device-form').reset(); devicePreset(); statusText('device-form-status', ''); $('device-dialog').showModal(); };
$('device-profile').onchange = devicePreset;
$('device-form').onsubmit = createDevice;
$('device-table').onclick = event => handleRowAction(event, 'dispositivos', state.devices);
$('reload-limits').onclick = () => busy($('reload-limits'), loadLimits);
$('limits-form').onsubmit = saveLimits;
$('reload-resource').onclick = () => busy($('reload-resource'), loadResource);
$('new-resource').onclick = () => openEditor(state.resource, 'create');
$('resource-table').onclick = event => handleRowAction(event, state.resource, state.resources);
$('editor-form').onsubmit = saveEditor;
$('confirm-delete').onclick = deleteConfirmed;
$('open-settings').onclick = openSettings; $('banner-settings').onclick = openSettings; $('header-settings').onclick = openSettings;
$('exit-demo').onclick = () => changeConnection(api.base, false).catch(error => toast(error.message, 'error'));
$('settings-form').onsubmit = async event => { event.preventDefault(); try { const base = normalizeBase($('api-url').value); await changeConnection(base, $('demo-option').checked); $('settings-dialog').close(); } catch (error) { toast(error.message, 'error'); } };
document.querySelectorAll('[data-close]').forEach(button => { button.onclick = () => button.closest('dialog').close(); });
window.addEventListener('hashchange', showPage);
// Sem envio no unload: o navegador não garante finalizar fetch/MQTT.
// Para encerrar os alarmes, o usuário desativa a automação antes de sair.
setInterval(() => { $('clock').textContent = `${new Intl.DateTimeFormat('pt-BR', { timeZone: 'America/Sao_Paulo', day: '2-digit', month: 'short' }).format(new Date())} · ${time(new Date().toISOString())}`; renderActuator(); }, 1000);
activity('Dashboard iniciada. Aguardando leituras da API.');
showPage(); void poll(); void queryActuator({ silent: true });
