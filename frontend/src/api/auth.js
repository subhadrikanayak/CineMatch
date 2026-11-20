import api from './client.js'

export const registerUser = (data) => api.post('/auth/register', data).then((r) => r.data)

// The backend login expects form fields (OAuth2), not JSON.
export const loginUser = (identifier, password) =>
  api
    .post('/auth/login', new URLSearchParams({ username: identifier, password }))
    .then((r) => r.data)

export const fetchMe = () => api.get('/auth/me').then((r) => r.data)