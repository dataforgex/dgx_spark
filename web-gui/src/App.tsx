import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Chat } from './components/Chat'
import { Dashboard } from './components/Dashboard'
import { Navigation } from './components/Navigation'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Navigation />
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
