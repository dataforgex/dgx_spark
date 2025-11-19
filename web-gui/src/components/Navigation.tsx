import { Link, useLocation } from 'react-router-dom'
import './Navigation.css'

export function Navigation() {
  const location = useLocation()

  return (
    <nav className="navigation">
      <div className="nav-container">
        <h1 className="nav-title">DGX Spark vLLM</h1>
        <div className="nav-links">
          <Link
            to="/chat"
            className={location.pathname === '/chat' ? 'nav-link active' : 'nav-link'}
          >
            Chat
          </Link>
          <Link
            to="/dashboard"
            className={location.pathname === '/dashboard' ? 'nav-link active' : 'nav-link'}
          >
            Dashboard
          </Link>
        </div>
      </div>
    </nav>
  )
}
