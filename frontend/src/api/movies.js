import api from './client.js'

const data = (r) => r.data

export const listMovies = (params) => api.get('/movies', { params }).then(data)
export const getMovie = (id) => api.get(`/movies/${id}`).then(data)
export const similarMovies = (id, limit = 8) =>
  api.get(`/movies/${id}/similar`, { params: { limit } }).then(data)
export const filterOptions = () => api.get('/meta/filters').then(data)

export const guestRecommendations = (body) => api.post('/recommendations', body).then(data)
export const myRecommendations = (params) => api.get('/recommendations/me', { params }).then(data)
export const hiddenGems = (params) => api.get('/recommendations/hidden-gems', { params }).then(data)
export const surprise = (body) => api.post('/recommendations/surprise', body).then(data)

export const semanticSearch = (body) => api.post('/search/semantic', body).then(data)

export const listMoods = () => api.get('/moods').then(data)
export const moodRecommend = (body) => api.post('/moods/recommend', body).then(data)