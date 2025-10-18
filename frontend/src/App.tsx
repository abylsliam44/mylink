import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom'
import EmployerAdmin from './pages/EmployerAdmin'
import CandidateWidget from './pages/CandidateWidget'
import Catalog from './pages/Catalog'
import Auth from './pages/Auth'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <header className="h-[64px] border-b border-grayx-300 bg-white">
          <div className="container h-full flex items-center justify-between">
            <Link to="/" className="font-semibold text-[18px] tracking-[-0.01em]">
              <span className="text-[#111827]">my</span>
              <span className="text-primary-600">link</span>
            </Link>
            <nav className="space-x-4 text-sm">
              <Link to="/" className="text-grayx-600 hover:text-grayx-900">Соискателям</Link>
              <Link to="/employer-admin" className="text-grayx-600 hover:text-grayx-900">Работодателям</Link>
              <Link to="/auth" className="text-grayx-600 hover:text-grayx-900">Вход</Link>
            </nav>
          </div>
        </header>
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Catalog />} />
            <Route path="/employer-admin" element={<EmployerAdmin />} />
            <Route path="/widget" element={<CandidateWidget />} />
            <Route path="/auth" element={<Auth />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <footer className="border-t border-grayx-300 bg-white text-center text-xs text-grayx-600 py-3">MyLink — HR Assistant</footer>
      </div>
    </BrowserRouter>
  )
}

export default App
