import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE_URL;

const api = axios.create({
  baseURL: API_BASE,
  timeout: 600000, // 10 min timeout for Hive queries
});

export const searchFlights = (params) => api.get('/search-flights', { params });
export const whereToFly = (params) => api.get('/where-to-fly', { params });
export const whenToFly = (params) => api.get('/when-to-fly', { params });
export const airlineComparison = (params) => api.get('/airline-comparison', { params });
export const searchAirports = (params) => api.get('/airports', { params });
export const chatbot = (question) => api.post('/chatbot', { question });
export const healthCheck = () => api.get('/health');

export default api;
