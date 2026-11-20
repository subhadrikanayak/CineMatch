import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { Bookmark, ChevronDown, Film, LogOut, Menu, Shield, User, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'

const LINKS = [
  { to: '/discover', label: 'Discover' },
  { to: '/moods', label: 'Moods' },
  { to: '/hidden-gems', label: 'Hidden Gems' },
  { to: '/people', label: 'Cast' },
  { to: '/compare', label: 'Compare' },
]

const linkClass = ({ isActive }) =>
  `text-sm transition-colors ${isActive ? 'text-gold' : 'text-mute hover:text-ink'}`

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  const signOut = () => {
    setMenuOpen(false)
    setMobileOpen(false)
    logout()
    navigate('/')
  }

  const menuItems = [
    { to: '/watchlist', label: 'Watchlist', icon: Bookmark },
    { to: '/profile', label: 'Profile', icon: User },
    { to: '/taste', label: 'Taste profile', icon: Film },
    ...(user?.role === 'admin' ? [{ to: '/admin', label: 'Admin', icon: Shield }] : []),
  ]

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-canvas/90 backdrop-blur">
      <div className="container-page flex h-16 items-center justify-between">
        <Link to="/" className="flex items-center gap-2 font-serif text-xl text-ink">
          <Film size={20} className="text-gold" />
          Cine<span className="text-gold">Match</span>
        </Link>

        <nav className="hidden items-center gap-7 md:flex">
          {LINKS.map((l) => (
            <NavLink key={l.to} to={l.to} className={linkClass}>
              {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          {user ? (
            <div className="relative">
              <button
                onClick={() => setMenuOpen((o) => !o)}
                className="flex items-center gap-2 rounded-lg border border-line px-3 py-1.5 text-sm hover:border-gold-dim"
              >
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gold text-xs font-medium text-canvas">
                  {user.username[0].toUpperCase()}
                </span>
                {user.username}
                <ChevronDown size={14} className="text-mute" />
              </button>
              {menuOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
                  <div className="absolute right-0 z-50 mt-2 w-48 rounded-xl border border-line bg-raised p-1 shadow-soft">
                    {menuItems.map(({ to, label, icon: Icon }) => (
                      <Link
                        key={to}
                        to={to}
                        onClick={() => setMenuOpen(false)}
                        className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-ink hover:bg-surface"
                      >
                        <Icon size={15} className="text-mute" /> {label}
                      </Link>
                    ))}
                    <button
                      onClick={signOut}
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-ink hover:bg-surface"
                    >
                      <LogOut size={15} className="text-mute" /> Log out
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <>
              <Link to="/login" className="btn-ghost">Log in</Link>
              <Link to="/register" className="btn-primary">Sign up</Link>
            </>
          )}
        </div>

        <button
          className="text-ink md:hidden"
          onClick={() => setMobileOpen((o) => !o)}
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {mobileOpen && (
        <div className="border-t border-line bg-canvas md:hidden">
          <div className="container-page flex flex-col gap-1 py-3">
            {[...LINKS, ...(user ? menuItems : [])].map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-2 text-sm ${isActive ? 'text-gold' : 'text-ink'}`
                }
              >
                {l.label}
              </NavLink>
            ))}
            {user ? (
              <button onClick={signOut} className="rounded-lg px-3 py-2 text-left text-sm text-ink">
                Log out
              </button>
            ) : (
              <div className="flex gap-3 px-3 pt-2">
                <Link to="/login" onClick={() => setMobileOpen(false)} className="btn-ghost flex-1">Log in</Link>
                <Link to="/register" onClick={() => setMobileOpen(false)} className="btn-primary flex-1">Sign up</Link>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  )
}