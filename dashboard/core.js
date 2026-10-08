/* Funções independentes da interface, compartilhadas com os testes. */
export const SENSOR_INFO = {
  temperatura: { name: 'Temperatura', unit: '°C', icon: 'thermometer', decimals: 1 },
  umidade: { name: 'Umidade', unit: '%', icon: 'drop', decimals: 1 },
  luminosidade: { name: 'Luminosidade', unit: 'ADC', icon: 'sun', decimals: 0 },
  brilho: { name: 'Brilho da lâmpada', unit: '%', icon: 'bulb', decimals: 0 }
};

export function normalizeBase(input) {
  const url = new URL(String(input).trim());
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error('Use um endereço HTTP ou HTTPS, sem credenciais, consulta ou fragmento.');
  }
  return url.href.replace(/\/+$/, '');
}

export function errorDetail(data) {
  const detail = data?.detail ?? data?.mensagem ?? data;
  if (Array.isArray(detail)) {
    return detail.map(item => `${(item.loc ?? []).filter(x => x !== 'body').join(' → ')}: ${item.msg ?? 'Valor inválido'}`).join('; ');
  }
  return typeof detail === 'string' ? detail : JSON.stringify(detail ?? 'Resposta inesperada.');
}

export class ApiClient {
  constructor(base, fetcher = globalThis.fetch) { this.base = normalizeBase(base); this.fetcher = (...args) => fetcher(...args); }
  async request(path, { method = 'GET', body, blob = false, timeout = 15000 } = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
      const response = await this.fetcher(`${this.base}${path}`, {
        method, signal: controller.signal, cache: 'no-store',
        headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body)
      });
      if (!response.ok) {
        let data;
        try { data = await response.json(); } catch { data = { detail: `Erro HTTP ${response.status}.` }; }
        const error = new Error(errorDetail(data));
        error.status = response.status;
        throw error;
      }
      if (blob) return await response.blob();
      if (response.status === 204) return null;
      const text = await response.text();
      return text ? JSON.parse(text) : null;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('A API demorou para responder. Confira a conexão e o servidor.');
      if (error instanceof TypeError) throw new Error('Não foi possível acessar a API. Confira se o FastAPI está rodando e se a origem está permitida no CORS.');
      throw error;
    } finally { clearTimeout(timer); }
  }
}

// TimeInstant é o horário da última atualização da entidade no Orion.
// Não é heartbeat individual de cada atributo ou confirmação do ESP monitor.
export function isFresh(timestamp, now = Date.now(), maxAge = 30000) {
  const value = Date.parse(timestamp);
  return Number.isFinite(value) && now - value >= -5000 && now - value <= maxAge;
}

export function validateAlertData(data) {
  const allowed = ['temperatura', 'umidade', 'luminosidade'];
  if (!data || !Array.isArray(data.alertas) || data.alertas.some(x => !allowed.includes(x)) || !data.sensores) {
    throw new Error('A API retornou um formato de alertas inesperado. Confira GET /alertas.');
  }
  for (const key of ['temperatura', 'umidade', 'luminosidade_bruta']) {
    const item = data.sensores[key];
    if (!item || typeof item.valor !== 'number' || !Number.isFinite(item.valor) || !['normal', 'fora_da_faixa', 'desativado'].includes(item.estado)) {
      throw new Error(`Leitura inválida para ${key}.`);
    }
  }
  return data;
}

export function validateLimits(data) {
  for (const key of ['temperatura', 'umidade', 'luminosidade_bruta']) {
    const item = data[key];
    if (!item || typeof item.ativo !== 'boolean' || !Number.isFinite(item.minimo) || !Number.isFinite(item.maximo)) throw new Error('Preencha todos os limites com números válidos.');
    if (item.minimo > item.maximo) throw new Error(`O mínimo de ${key} não pode ser maior que o máximo.`);
    if (key === 'umidade' && (item.minimo < 0 || item.maximo > 100)) throw new Error('A umidade deve ficar entre 0 e 100%.');
    if (key === 'luminosidade_bruta' && (!Number.isInteger(item.minimo) || !Number.isInteger(item.maximo) || item.minimo < 0 || item.maximo > 4095)) throw new Error('Use números inteiros de 0 a 4095 para o LDR.');
  }
  return data;
}

export function unwrapList(data, resource) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.[resource])) return data[resource];
  const aliases = { dispositivos: 'devices', servicos: 'services' };
  if (Array.isArray(data?.[aliases[resource]])) return data[aliases[resource]];
  throw new Error('O servidor retornou uma lista em formato inesperado.');
}

export function resourceMutation(resource, action, item) {
  const encoded = encodeURIComponent(item.id ?? item.device_id ?? '');
  if (action === 'create') return { path: `/${resource}`, method: 'POST' };
  if (resource === 'servicos') {
    const query = new URLSearchParams({ apikey: item.apikey ?? '', resource: item.resource ?? '' });
    return { path: `/servicos?${query}`, method: action === 'delete' ? 'DELETE' : 'PUT' };
  }
  if (resource === 'registros' && action === 'edit') throw new Error('A API atual não oferece edição de registros.');
  return {
    path: `/${resource}/${encoded}${resource === 'entidades' && action === 'edit' ? '/attrs' : ''}`,
    method: action === 'delete' ? 'DELETE' : resource === 'dispositivos' ? 'PUT' : 'PATCH'
  };
}

// Compatibilidade com Excel em português e proteção contra fórmulas em células.
export function csvHistory(records) {
  const cell = value => {
    let text = String(value ?? '');
    if (/^[=+@-]/.test(text)) text = `'${text}`;
    return `"${text.replaceAll('"', '""')}"`;
  };
  return '\ufeff' + ['data_iso;valor', ...records.map(row => `${cell(row.data)};${cell(row.valor)}`)].join('\r\n');
}
