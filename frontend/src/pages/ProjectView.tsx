import { useState, useEffect, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft,
  Download,
  Folder,
  Edit2,
  Check,
  Disc3,
  ExternalLink,
  Plus,
  Search,
  Archive,
} from 'lucide-react'
import { api, type Project } from '../lib/api'
import { TrackRow } from '../components/TrackRow'
import { InputHero } from '../components/InputHero'
import { upsertTracks, allTracks, useStoreVersion } from '../lib/store'
import { toast } from 'sonner'

export function ProjectView() {
  const { id } = useParams<{ id: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [editingName, setEditingName] = useState(false)
  const [nameVal, setNameVal] = useState('')
  const [showAddTracks, setShowAddTracks] = useState(false)
  const [filter, setFilter] = useState<'all' | 'review' | 'extended' | 'done'>('all')
  const [searchQuery, setSearchQuery] = useState('')

  // Subscribes to live WebSocket changes
  useStoreVersion()

  const loadProject = async () => {
    if (!id) return
    try {
      const p = await api.project(id)
      setProject(p)
      setNameVal(p.name)
      upsertTracks(p.tracks)
    } catch (e) {
      toast.error('Erro ao carregar projeto: ' + (e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProject()
  }, [id])

  // Merge store tracks into current project view
  const currentTracks = useMemo(() => {
    if (!project) return []
    const storeMap = new Map(allTracks().map((t) => [t.id, t]))
    return project.tracks.map((t) => storeMap.get(t.id) || t)
  }, [project, allTracks()])

  const handleSaveName = async () => {
    if (!id || !nameVal.trim()) return
    try {
      const updated = await api.renameProject(id, nameVal.trim())
      setProject((prev) => (prev ? { ...prev, name: updated.name } : null))
      setEditingName(false)
      toast.success('Nome atualizado!')
    } catch (err) {
      toast.error('Erro ao renomear: ' + (err as Error).message)
    }
  }

  const handleDownloadAll = async () => {
    if (!id) return
    try {
      const res = await api.download({ project_id: id, include_low: false })
      toast.success(`${res.queued} faixa(s) adicionada(s) à fila de download!`)
    } catch (err) {
      toast.error('Erro ao iniciar downloads: ' + (err as Error).message)
    }
  }

  const handleReveal = async () => {
    if (!id) return
    try {
      await api.reveal(id)
      toast.success('Pasta aberta no Finder!')
    } catch (err) {
      toast.error('Erro ao abrir pasta: ' + (err as Error).message)
    }
  }

  // Filter calculations
  const total = currentTracks.length
  const doneTracks = currentTracks.filter((t) => t.download?.status === 'done')
  const reviewTracks = currentTracks.filter(
    (t) => (t.confidence === 'medium' || t.confidence === 'low' || t.status === 'not_found') && !t.user_confirmed
  )
  const extendedTracks = currentTracks.filter(
    (t) => t.alternatives && t.alternatives.some((a) => a.alt_kind === 'extended')
  )

  const filteredTracks = useMemo(() => {
    let list = currentTracks

    if (filter === 'review') {
      list = list.filter(
        (t) => (t.confidence === 'medium' || t.confidence === 'low' || t.status === 'not_found') && !t.user_confirmed
      )
    } else if (filter === 'extended') {
      list = list.filter((t) => t.alternatives && t.alternatives.some((a) => a.alt_kind === 'extended'))
    } else if (filter === 'done') {
      list = list.filter((t) => t.download?.status === 'done')
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      list = list.filter(
        (t) =>
          t.source.title.toLowerCase().includes(q) ||
          t.source.artists.some((a) => a.toLowerCase().includes(q)) ||
          t.selected?.title.toLowerCase().includes(q)
      )
    }

    return list
  }, [currentTracks, filter, searchQuery])

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-40 rounded-3xl bg-white/5" />
        <div className="h-64 rounded-2xl bg-white/5" />
      </div>
    )
  }

  if (!project) {
    return (
      <div className="text-center py-20">
        <p className="text-zinc-400">Projeto não encontrado.</p>
        <Link to="/" className="btn btn-primary mt-4 text-xs">
          Voltar para o início
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Botão voltar */}
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white transition"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        <span>Todos os projetos</span>
      </Link>

      {/* Header do projeto */}
      <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.08] to-white/[0.02] p-6 backdrop-blur-xl">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className="relative h-24 w-24 shrink-0 overflow-hidden rounded-2xl bg-white/10 shadow-xl">
              {project.cover ? (
                <img src={project.cover} alt={project.name} className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-zinc-500">
                  <Disc3 className="h-10 w-10" />
                </div>
              )}
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-2">
                {editingName ? (
                  <div className="flex items-center gap-2">
                    <input
                      className="input text-base font-bold py-1 h-9"
                      value={nameVal}
                      onChange={(e) => setNameVal(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSaveName()}
                      autoFocus
                    />
                    <button onClick={handleSaveName} className="btn btn-primary h-9 px-3 text-xs">
                      <Check className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 group">
                    <h1 className="text-2xl font-bold tracking-tight text-white font-['Space_Grotesk']">
                      {project.name}
                    </h1>
                    <button
                      onClick={() => setEditingName(true)}
                      className="opacity-0 group-hover:opacity-100 btn-icon h-7 w-7 transition"
                      title="Renomear projeto"
                    >
                      <Edit2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-400">
                <span className="font-semibold text-zinc-200">{total} faixas</span>
                <span>·</span>
                <span className="text-emerald-400 font-medium">{doneTracks.length} baixadas</span>
                {project.source_url && (
                  <>
                    <span>·</span>
                    <a
                      href={project.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-zinc-400 hover:text-white transition"
                    >
                      <span>Abrir no Spotify</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Ações principais */}
          <div className="flex flex-wrap items-center gap-2 self-stretch md:self-auto justify-end">
            <button
              onClick={() => setShowAddTracks(!showAddTracks)}
              className="btn btn-ghost text-xs"
            >
              <Plus className="h-4 w-4" />
              <span>Adicionar Músicas</span>
            </button>

            <button onClick={handleReveal} className="btn btn-ghost text-xs" title="Abrir pasta no Finder">
              <Folder className="h-4 w-4" />
              <span>Pasta no Mac</span>
            </button>

            {doneTracks.length > 0 && (
              <a
                href={`/api/projects/${project.id}/zip`}
                className="btn btn-ghost text-xs text-zinc-200"
                title="Baixar ZIP com todas as músicas"
              >
                <Archive className="h-4 w-4" />
                <span>Baixar ZIP ({doneTracks.length})</span>
              </a>
            )}

            <button onClick={handleDownloadAll} className="btn btn-primary text-xs">
              <Download className="h-4 w-4" />
              <span>Baixar Tudo</span>
            </button>
          </div>
        </div>

        {/* Input colapsável de adicionar mais músicas */}
        {showAddTracks && (
          <div className="mt-6 pt-6 border-t border-white/10">
            <InputHero projectId={project.id} onTracksAdded={loadProject} />
          </div>
        )}
      </div>

      {/* Barra de Filtros e Busca */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
          <button
            onClick={() => setFilter('all')}
            className={`rounded-xl px-3 py-1.5 text-xs font-medium transition ${
              filter === 'all'
                ? 'bg-white/10 text-white border border-white/10'
                : 'text-zinc-400 hover:text-white hover:bg-white/5'
            }`}
          >
            Todas ({total})
          </button>

          <button
            onClick={() => setFilter('review')}
            className={`rounded-xl px-3 py-1.5 text-xs font-medium transition flex items-center gap-1.5 ${
              filter === 'review'
                ? 'bg-amber-400/10 text-amber-300 border border-amber-400/20'
                : 'text-zinc-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <span>🟡 Para revisar</span>
            <span className="rounded-full bg-amber-400/20 px-1.5 text-[10px]">{reviewTracks.length}</span>
          </button>

          <button
            onClick={() => setFilter('extended')}
            className={`rounded-xl px-3 py-1.5 text-xs font-medium transition flex items-center gap-1.5 ${
              filter === 'extended'
                ? 'bg-fuchsia-400/10 text-fuchsia-300 border border-fuchsia-400/20'
                : 'text-zinc-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <span>🎛️ Com Extended</span>
            <span className="rounded-full bg-fuchsia-400/20 px-1.5 text-[10px]">{extendedTracks.length}</span>
          </button>

          <button
            onClick={() => setFilter('done')}
            className={`rounded-xl px-3 py-1.5 text-xs font-medium transition flex items-center gap-1.5 ${
              filter === 'done'
                ? 'bg-emerald-400/10 text-emerald-300 border border-emerald-400/20'
                : 'text-zinc-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <span>✅ Baixadas</span>
            <span className="rounded-full bg-emerald-400/20 px-1.5 text-[10px]">{doneTracks.length}</span>
          </button>
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-zinc-500" />
          <input
            className="input text-xs pl-8 h-8"
            placeholder="Filtrar por nome ou artista..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Lista de faixas */}
      <div className="space-y-1.5">
        <div className="grid grid-cols-[28px_minmax(0,1.2fr)_minmax(0,1.3fr)_90px_190px_36px] items-center gap-4 px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
          <span className="text-right">#</span>
          <span>Faixa de Origem</span>
          <span>Versão YouTube Music</span>
          <span>Confiança</span>
          <span className="text-right">Download & Bitrate</span>
          <span />
        </div>

        {filteredTracks.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/10 p-12 text-center text-xs text-zinc-500">
            Nenhuma música encontrada neste filtro.
          </div>
        ) : (
          filteredTracks.map((track, idx) => (
            <TrackRow key={track.id} track={track} index={idx} />
          ))
        )}
      </div>
    </div>
  )
}
