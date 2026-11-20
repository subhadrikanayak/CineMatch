import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import Home from './pages/Home.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import ComingSoon from './pages/ComingSoon.jsx'
import NotFound from './pages/NotFound.jsx'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Placeholders: each is replaced by a real page in Phase 10 */}
        <Route path="/discover" element={<ComingSoon title="Discover" />} />
        <Route path="/moods" element={<ComingSoon title="Mood picker" />} />
        <Route path="/hidden-gems" element={<ComingSoon title="Hidden gems" />} />
        <Route path="/people" element={<ComingSoon title="Actors and actresses" />} />
        <Route path="/compare" element={<ComingSoon title="Compare movies" />} />
        <Route path="/movies/:id" element={<ComingSoon title="Movie details" />} />

        <Route element={<ProtectedRoute />}>
          <Route path="/watchlist" element={<ComingSoon title="Watchlist" />} />
          <Route path="/profile" element={<ComingSoon title="Profile" />} />
          <Route path="/taste" element={<ComingSoon title="Taste profile" />} />
        </Route>
        <Route element={<ProtectedRoute admin />}>
          <Route path="/admin" element={<ComingSoon title="Admin dashboard" />} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}