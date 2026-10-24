import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles, ArrowRight, Loader2, Music, PlaySquare, ListMusic } from 'lucide-react'
import { api } from '../lib/api'
import { toast } from 'sonner'

export function InputHero({
  projectId,
  onTracksAdded,
}: {
  projectId?: string
  onTracksAdded?: () => void
}) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [multiline, setMultiline] = useState(false)
  const navigate = useNavigate()
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed) {
      toast.error('Cole um link ou digite uma música.')
      return
    }

    setLoading(true)
    try {
      const res = await api.resolve(trimmed, projectId)
      toast.success(
        res.kind === 'playlist'
          ? `Playlist carregada! ${res.count} faixas encontradas.`
          : `${res.count} faixa(s) adicionada(s)!`
      )
      setInput('')
      if (onTracksAdded) {
        onTracksAdded()
      } else if (res.project_id) {
        navigate(`/project/${res.project_id}`)
      }
    } catch (err) {
      toast.error((err as Error).message || 'Erro ao processar entrada.')
    } finally {
      setLoading(false)
    }
  }

  // Detect multiline paste automatically
  const handleChange = (val: string) => {
    setInput(val)
    if (val.includes('\n') && !multiline) {
      setMultiline(true)
    }
  }

  return (
    <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.06] to-white/[0.02] p-6 shadow-2xl backdrop-blur-2xl">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
        <div>
          <h2 className="text-xl md:text-2xl font-bold tracking-tight text-white flex items-center gap-2 font-['Space_Grotesk']">
            <Sparkles className="h-5 w-5 text-accent" />
            {projectId ? 'Adicionar mais faixas ao projeto' : 'Importar Playlist ou Música'}
          </h2>
          <p className="text-xs md:text-sm text-zinc-400 mt-1">
            Cole playlist do Spotify, link do YouTube Music, ou copie e cole a lista de músicas do Spotify Desktop.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setMultiline(!multiline)}
          className="self-start md:self-auto rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-medium text-zinc-300 hover:bg-white/10 transition"
        >
          {multiline ? 'Modo linha única' : 'Colar várias linhas (Cmd+V)'}
        </button>
      </div>

      <form onSubmit={handleSubmit} className="relative">
        <div className="relative flex items-start rounded-2xl border border-white/10 bg-black/40 shadow-inner focus-within:border-accent/60 focus-within:ring-2 focus-within:ring-accent/20 transition">
          {multiline ? (
            <textarea
              ref={textareaRef}
              rows={4}
              value={input}
              onChange={(e) => handleChange(e.target.value)}
              placeholder="Cole vários links ou linhas:&#10;Daft Punk - One More Time&#10;https://open.spotify.com/track/...&#10;David Guetta - Titanium"
              className="w-full resize-y bg-transparent p-4 text-sm text-white placeholder:text-zinc-600 focus:outline-none"
              disabled={loading}
            />
          ) : (
            <input
              type="text"
              value={input}
              onChange={(e) => handleChange(e.target.value)}
              placeholder="Cole o link da Playlist do Spotify, faixa, ou 'Artista - Nome da música'..."
              className="w-full bg-transparent px-4 py-4 text-sm text-white placeholder:text-zinc-600 focus:outline-none"
              disabled={loading}
            />
          )}

          <div className="p-2">
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="btn btn-primary h-11 px-5 font-semibold text-xs md:text-sm shrink-0"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Buscando...</span>
                </>
              ) : (
                <>
                  <span>{projectId ? 'Adicionar' : 'Processar'}</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </div>
        </div>
      </form>

      <div className="mt-4 flex flex-wrap items-center gap-2 text-[11px] text-zinc-500">
        <span className="font-medium text-zinc-400">Suporta:</span>
        <span className="inline-flex items-center gap-1 rounded-md bg-white/5 px-2 py-0.5">
          <ListMusic className="h-3 w-3 text-emerald-400" /> Playlists do Spotify
        </span>
        <span className="inline-flex items-center gap-1 rounded-md bg-white/5 px-2 py-0.5">
          <PlaySquare className="h-3 w-3 text-rose-400" /> YouTube & YT Music
        </span>
        <span className="inline-flex items-center gap-1 rounded-md bg-white/5 px-2 py-0.5">
          <Music className="h-3 w-3 text-accent" /> "Artista - Faixa"
        </span>
      </div>
    </div>
  )
}
