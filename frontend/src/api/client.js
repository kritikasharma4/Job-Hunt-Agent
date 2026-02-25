import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

export const profileApi = {
  getCurrent: () => api.get('/profiles/current'),
  create: (data) => api.post('/profiles', data),
  update: (userId, data) => api.put(`/profiles/${userId}`, data),
  upload: (file) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/profiles/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

export const jobsApi = {
  search: (params) => api.post('/jobs/search', params),
  list: (params) => api.get('/jobs', { params }),
  get: (jobId) => api.get(`/jobs/${jobId}`),
};

export const matchesApi = {
  list: (params) => api.get('/matches', { params }),
  get: (matchId) => api.get(`/matches/${matchId}`),
  delete: (matchId) => api.delete(`/matches/${matchId}`),
  stats: () => api.get('/matches/stats'),
};

export const applicationsApi = {
  create: (data) => api.post('/applications', data),
  list: (params) => api.get('/applications', { params }),
  updateStatus: (id, data) => api.patch(`/applications/${id}`, data),
  delete: (id) => api.delete(`/applications/${id}`),
};

export default api;
