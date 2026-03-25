import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE_URL;

function normalizeBase(url) {
  return (url || '').replace(/\/+$/, '');
}

function getFallbackBases(base) {
  const normalized = normalizeBase(base);
  if (!normalized) return [];

  const fallbacks = [];
  if (normalized.endsWith('/api.now')) {
    fallbacks.push(normalized.replace(/\/api\.now$/, '/api'));
  } else if (normalized.endsWith('/api')) {
    fallbacks.push(`${normalized}.now`);
  }

  return fallbacks;
}

const PRIMARY_BASE = normalizeBase(API_BASE);
const FALLBACK_BASES = getFallbackBases(PRIMARY_BASE);

function createClient(baseURL) {
  return axios.create({
    baseURL,
    timeout: 900000, // increased to 15m for extremely slow Hive queries
  });
}

const api = createClient(PRIMARY_BASE);

async function requestWithFallback(config) {
  const clients = [api, ...FALLBACK_BASES.map(createClient)];
  let lastError;

  for (const client of clients) {
    try {
      return await client.request(config);
    } catch (err) {
      lastError = err;
      const status = err?.response?.status;
      const isNetworkError = !err?.response;
      if (status !== 404 && !isNetworkError) {
        throw err;
      }
    }
  }

  throw lastError;
}

export const searchFlights = (params) => requestWithFallback({ method: 'get', url: '/search-flights', params });
export const whereToFly = (params) => requestWithFallback({ method: 'get', url: '/where-to-fly', params });
export async function whenToFly(params) {
  try {
    return await requestWithFallback({ method: 'get', url: '/when-to-fly', params });
  } catch (err) {
    const status = err?.response?.status;
    const message = String(err?.response?.data?.error || '').toLowerCase();
    const needsRawFallback = status === 503 && (message.includes('aggregate') || message.includes('schema mismatch'));
    if (!needsRawFallback) throw err;

    const retryParams = {
      ...params,
      allowRaw: 1,
      // Reduced sample size to prevent timeouts on slow backends
      rawSampleCap: params?.rawSampleCap || 10000, 
    };
    return requestWithFallback({ method: 'get', url: '/when-to-fly', params: retryParams });
  }
}

export async function airlineComparison(params) {
  try {
    return await requestWithFallback({ method: 'get', url: '/airline-comparison', params });
  } catch (err) {
    const status = err?.response?.status;
    const message = String(err?.response?.data?.error || '').toLowerCase();
    const needsRawFallback = status === 503 && (message.includes('aggregate') || message.includes('schema mismatch'));
    if (!needsRawFallback) throw err;

    const retryParams = {
      ...params,
      allowRaw: 1,
      // Reduced sample size to prevent timeouts on slow backends
      rawSampleCap: params?.rawSampleCap || 10000,
    };
    return requestWithFallback({ method: 'get', url: '/airline-comparison', params: retryParams });
  }
}
export const searchAirports = (params) => requestWithFallback({ method: 'get', url: '/airports', params });
export const chatbot = (question) => requestWithFallback({ method: 'post', url: '/chatbot', data: { question } });
export const healthCheck = () => requestWithFallback({ method: 'get', url: '/health' });

export default api;
