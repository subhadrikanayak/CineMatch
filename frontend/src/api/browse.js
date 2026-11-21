import api from './client.js'

const data = (r) => r.data

export const searchPeople = (q, gender) =>
  api.get('/people', { params: { q, gender: gender || undefined } }).then(data)
export const getPerson = (id) => api.get(`/people/${id}`).then(data)
export const personMovies = (id, params) => api.get(`/people/${id}/movies`, { params }).then(data)
export const moviesTogether = (a, b) =>
  api.get('/people/together', { params: { a, b, page_size: 50 } }).then(data)

export const quickSearch = (q, limit = 6) => api.get('/search', { params: { q, limit } }).then(data)
export const compareMovies = (a, b) => api.get('/compare', { params: { a, b } }).then(data)