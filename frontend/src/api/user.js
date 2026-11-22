import api from './client.js'

const data = (r) => r.data

export const movieState = (id) => api.get(`/users/me/movie-state/${id}`).then(data)
export const rateMovie = (id, rating) => api.put(`/ratings/${id}`, { rating }).then(data)
export const unrateMovie = (id) => api.delete(`/ratings/${id}`)
export const addWatchlist = (id) => api.post(`/watchlist/${id}`).then(data)
export const removeWatchlist = (id) => api.delete(`/watchlist/${id}`)
export const markWatched = (id) => api.post(`/watch-history/${id}`).then(data)
export const unmarkWatched = (id) => api.delete(`/watch-history/${id}`)
export const react = (id, type) =>
  api.post('/feedback', { movie_id: id, feedback_type: type }).then(data)
export const clearReaction = (id) => api.delete(`/feedback/${id}`)
export const listComments = (id) => api.get(`/feedback/movie/${id}`).then(data)
export const addComment = (id, comment) =>
  api.post('/feedback', { movie_id: id, feedback_type: 'comment', comment }).then(data)
export const deleteComment = (commentId) => api.delete(`/feedback/comment/${commentId}`)