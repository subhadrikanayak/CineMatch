import api from './client.js'

export const listMovies = (params) => api.get('/movies', { params }).then((r) => r.data)

export const guestRecommendations = (body) =>
  api.post('/recommendations', body).then((r) => r.data)

export const myRecommendations = (params) =>
  api.get('/recommendations/me', { params }).then((r) => r.data)