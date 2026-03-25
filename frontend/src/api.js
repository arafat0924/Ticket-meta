import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://192.168.56.105:5000/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 600000, // 10 min timeout for Hive queries (analytics scan ~80M rows)
});

export const searchFlights = (params) => api.get('/search-flights', { params });
export const whereToFly = (params) => api.get('/where-to-fly', { params });
export const whenToFly = (params) => api.get('/when-to-fly', { params });
export const airlineComparison = (params) => api.get('/airline-comparison', { params });
export const searchAirports = (params) => api.get('/airports', { params });
export const healthCheck = () => api.get('/health');

// Analytics endpoints
export const analyticsOverview = () => api.get('/analytics/overview');
export const analyticsTopAirlines = () => api.get('/analytics/top-airlines');
export const analyticsDayOfWeek = () => api.get('/analytics/day-of-week');
export const analyticsBookingWindow = () => api.get('/analytics/booking-window');
export const analyticsWeekendMidweek = () => api.get('/analytics/weekend-midweek');
export const analyticsEconomyGap = () => api.get('/analytics/economy-gap');

// Flight Splicing
export const flightSplicing = (params) => api.get('/flight-splicing', { params });

// Where to Fly with budget + distance
export const whereToFlyBudget = (params) => api.get('/where-to-fly-budget', { params });

// Data Enrichment endpoints
export const enrichmentWeather = (airport) => api.get('/enrichment/weather', { params: { airport } });
export const enrichmentWealth = () => api.get('/enrichment/wealth');
export const enrichmentBrand = () => api.get('/enrichment/brand');
export const enrichmentRail = () => api.get('/enrichment/rail');
export const enrichmentGhost = () => api.get('/enrichment/ghost');

// Legacy non-streaming chatbot (fallback)
export const chatbot = (question, history = []) => api.post('/chatbot', { question, history });

/**
 * Streaming chatbot via SSE — calls onEvent for each server-sent chunk.
 * Returns an AbortController so caller can cancel.
 *
 * Event types: status, sql, answer, error, done
 */
export function chatbotStream(question, history = [], onEvent) {
  const controller = new AbortController();

  fetch(`${API_BASE}/chatbot/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, history }),
    signal: controller.signal,
  })
    .then(async (response) => {
      // If streaming endpoint returns 404 or error, fall back to non-streaming
      if (!response.ok) {
        console.warn(`Stream endpoint returned ${response.status}, falling back to non-streaming...`);
        return fallbackToNonStreaming(question, history, onEvent, controller.signal);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Parse SSE lines
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6));
              onEvent(event);
            } catch {
              // ignore parse errors on partial chunks
            }
          }
        }
      }

      // Process any remaining buffer
      if (buffer.startsWith('data: ')) {
        try {
          const event = JSON.parse(buffer.slice(6));
          onEvent(event);
        } catch { /* ignore */ }
      }

      // Ensure done is fired
      onEvent({ type: 'done' });
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        // Try fallback on network errors too
        console.warn('Stream failed, trying non-streaming fallback:', err.message);
        fallbackToNonStreaming(question, history, onEvent, controller.signal);
      }
    });

  return controller;
}

/**
 * Fallback: use the non-streaming /chatbot endpoint when streaming is unavailable.
 */
async function fallbackToNonStreaming(question, history, onEvent, signal) {
  try {
    onEvent({ type: 'status', message: 'Processing (non-streaming mode)...' });
    const res = await api.post('/chatbot', { question, history }, { signal });
    const data = res.data;

    if (data.error && !data.answer) {
      onEvent({ type: 'error', message: data.error });
    } else {
      if (data.sql) {
        onEvent({ type: 'sql', sql: data.sql });
      }
      onEvent({
        type: 'answer',
        answer: data.answer || 'No response received.',
        sql: data.sql || null,
        results: data.results || null,
      });
    }
  } catch (err) {
    if (err.name !== 'AbortError' && err.name !== 'CanceledError') {
      const msg = err.response?.data?.error || err.response?.data?.answer || err.message;
      onEvent({ type: 'error', message: msg });
    }
  }
  onEvent({ type: 'done' });
}

export default api;
