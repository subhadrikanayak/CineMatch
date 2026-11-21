import api from './client.js'

const data = (r) => r.data
const page = (page) => ({ params: { page, page_size: 24 } })

export const getWatchlist = (p) => api.get('/watchlist', page(p)).then(data)
export const getRatings = (p) => api.get('/ratings', page(p)).then(data)
export const getHistory = (p) => api.get('/users/me/history', page(p)).then(data)
export const getRecent = (limit = 12) => api.get('/users/me/recent', { params: { limit } }).then(data)

export const getPreferences = () => api.get('/users/me/preferences').then(data)
export const savePreferences = (body) => api.put('/users/me/preferences', body).then(data)
export const getTaste = () => api.get('/users/me/taste-profile').then(data)