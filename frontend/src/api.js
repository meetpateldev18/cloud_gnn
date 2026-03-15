import axios from 'axios';

// Change this to your EC2 public IP when deploying to AWS
// Example: const API_BASE = 'http://54.123.45.67:8000';
const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
});

export const getMachines   = () => api.get('/machines');
export const getMetrics    = () => api.get('/metrics');
export const getComparison = () => api.get('/comparison');
export const getGraph      = () => api.get('/graph');
export const getHealth     = () => api.get('/health');
export const getTasks      = () => api.get('/tasks');
export const scheduleTask  = (data) => api.post('/schedule_task', data);

export default api;
