import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'sonner'
import { PlayerProvider } from './lib/player'
import { Navbar } from './components/Navbar'
import { SettingsModal } from './components/SettingsModal'
import { HomeView } from './pages/HomeView'
import { ProjectView } from './pages/ProjectView'

export function App() {
  const [settingsOpen, setSettingsOpen] = useState(false)

  return (
    <PlayerProvider>
      <BrowserRouter>
        <div className="min-h-screen flex flex-col bg-ink text-zinc-100 selection:bg-accent selection:text-ink">
          <Navbar onOpenSettings={() => setSettingsOpen(true)} />

          <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-8 sm:px-6">
            <Routes>
              <Route path="/" element={<HomeView />} />
              <Route path="/project/:id" element={<ProjectView />} />
            </Routes>
          </main>

          <footer className="border-t border-white/[0.06] py-6 text-center text-xs text-zinc-500">
            <p>DJ Downloader &bull; YouTube Music 256kbps &bull; Motor de Match Inteligente</p>
          </footer>

          <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
          <Toaster theme="dark" position="bottom-right" richColors />
        </div>
      </BrowserRouter>
    </PlayerProvider>
  )
}

export default App
