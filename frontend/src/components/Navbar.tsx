import { Settings, Disc3 } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { useLiveConnection } from '../lib/store'
import { usePlayer } from '../lib/player'
import { Equalizer } from './ui'

export function Navbar({ onOpenSettings }: { onOpenSettings: () => void }) {
  const location = useLocation()
  const live = useLiveConnection()
  const player = usePlayer()

  return (
    <header className="sticky top-0 z-40 border-b border-white/[0.08] bg-ink/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2.5 font-bold tracking-tight text-white transition hover:opacity-90">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-accent to-accent-2 text-ink shadow-[0_0_20px_rgba(163,255,92,0.3)]">
              <Disc3 className="h-5 w-5 animate-[spin_8s_linear_infinite]" />
            </div>
            <div>
              <span className="font-['Space_Grotesk'] text-lg font-bold">DJ Downloader</span>
              <span className="ml-2 rounded-md bg-white/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-accent">Pro</span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            <Link
              to="/"
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                location.pathname === '/' ? 'bg-white/10 text-white' : 'text-zinc-400 hover:text-white hover:bg-white/5'
              }`}
            >
              Início & Projetos
            </Link>
          </nav>
        </div>

        {/* Player preview widget if playing */}
        {player.current && (
          <div className="flex items-center gap-3 rounded-full border border-accent/20 bg-accent/10 px-3 py-1 text-xs text-accent">
            <Equalizer />
            <span className="font-medium">Ouvindo prévia</span>
            <button
              onClick={() => player.stop()}
              className="ml-1 rounded-full bg-accent/20 px-2 py-0.5 text-[10px] text-white hover:bg-accent/30"
            >
              Parar
            </button>
          </div>
        )}

        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-zinc-400 mr-2">
            <span className={`inline-block h-2 w-2 rounded-full ${live ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-zinc-600'}`} />
            {live ? 'Online' : 'Conectando...'}
          </div>

          <button
            onClick={onOpenSettings}
            className="btn btn-ghost text-xs"
            title="Configurações (formato, cookies Chrome, pasta)"
          >
            <Settings className="h-4 w-4 text-zinc-300" />
            <span className="hidden sm:inline">Configurações</span>
          </button>
        </div>
      </div>
    </header>
  )
}
