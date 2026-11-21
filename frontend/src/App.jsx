import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import Home from './pages/Home.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import Discover from './pages/Discover.jsx'
import MovieDetail from './pages/MovieDetail.jsx'
import Moods from './pages/Moods.jsx'
import HiddenGems from './pages/HiddenGems.jsx'
import ComingSoon from './pages/ComingSoon.jsx'
import NotFound from './pages/NotFound.jsx'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        <Route path="/discover" element={<Discover />} />
        <Route path="/movies/:id" element={<MovieDetail />} />
        <Route path="/moods" element={<Moods />} />
        <Route path="/hidden-gems" element={<HiddenGems />} />

        {/* Built in Phase 10B */}
        <Route path="/people" element={<ComingSoon title="Actors and actresses" />} />
        <Route path="/people/:id" element={<ComingSoon title="Actor profile" />} />
        <Route path="/compare" element={<ComingSoon title="Compare movies" />} />

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