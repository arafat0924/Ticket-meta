import axios from 'axios';

const API_BASE = 'http://192.168.56.101:5000/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 300000, // 5 min timeout for Hive queries
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
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onEvent({ type: 'error', message: err.message });
        onEvent({ type: 'done' });
      }
    });

  return controller;
}

export default api;
