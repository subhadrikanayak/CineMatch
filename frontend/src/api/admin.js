import api from './client.js'

const data = (r) => r.data

export const stats = () => api.get('/admin/stats').then(data)
export const catalogue = (params) => api.get('/admin/movies', { params }).then(data)
export const usersActivity = (page) =>
  api.get('/admin/users-activity', { params: { page, page_size: 15 } }).then(data)
export const popularMovies = (by) => api.get('/admin/popular-movies', { params: { by, limit: 10 } }).then(data)
export const languageTrends = () => api.get('/admin/trends/languages').then(data)
export const genreTrends = () => api.get('/admin/trends/genres').then(data)
export const recAnalytics = () => api.get('/admin/recommendation-analytics').then(data)
export const retrain = () => api.post('/admin/retrain').then(data)
export const startIngest = (body) => api.post('/admin/ingest', body).then(data)
export const ingestStatus = () => api.get('/admin/ingest/status').then(data)