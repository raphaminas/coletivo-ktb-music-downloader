import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Disc3, Folder, Download, Trash2, ArrowUpRight, Music2 } from 'lucide-react'
import { api, type ProjectMeta } from '../lib/api'
import { InputHero } from '../components/InputHero'
import { toast } from 'sonner'

export function HomeView() {
  const [projects, setProjects] = useState<ProjectMeta[]>([])
  const [loading, setLoading] = useState(true)

  const loadProjects = async () => {
    try {
      const list = await api.projects()
      setProjects(list)
    } catch (e) {
      toast.error('Erro ao listar projetos: ' + (e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProjects()
  }, [])

  const handleDelete = async (pid: string, name: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm(`Deseja remover o projeto "${name}"?`)) return
    try {
      await api.deleteProject(pid)
      toast.success('Projeto removido')
      setProjects((prev) => prev.filter((p) => p.id !== pid))
    } catch (err) {
      toast.error('Erro ao deletar: ' + (err as Error).message)
    }
  }

  const handleReveal = async (pid: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    try {
      await api.reveal(pid)
      toast.success('Pasta aberta no Finder!')
    } catch (err) {
      toast.error('Erro ao abrir pasta: ' + (err as Error).message)
    }
  }

  return (
    <div className="space-y-10">
      <InputHero />

      {/* Projetos / Histórico */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="font-['Space_Grotesk'] text-xl font-bold text-white">Projetos & Playlists</h3>
            <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-zinc-400">
              {projects.length}
            </span>
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((n) => (
              <div key={n} className="h-32 animate-pulse rounded-2xl bg-white/5 border border-white/5" />
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 p-12 text-center">
            <Music2 className="h-10 w-10 text-zinc-600 mb-3" />
            <p className="text-sm text-zinc-400 font-medium">Nenhum projeto encontrado</p>
            <p className="text-xs text-zinc-500 mt-1 max-w-sm">
              Cole uma playlist do Spotify acima para criar seu primeiro projeto de casamento ou evento.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((p) => {
              const done = p.done_count ?? 0
              const total = p.track_count ?? 0
              const pct = total > 0 ? Math.round((done / total) * 100) : 0

              return (
                <Link
                  key={p.id}
                  to={`/project/${p.id}`}
                  className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03] p-4 transition hover:border-accent/40 hover:bg-white/[0.06] hover:shadow-[0_0_30px_rgba(163,255,92,0.06)]"
                >
                  <div className="flex items-start gap-3.5">
                    <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-xl bg-white/10 shadow-md">
                      {p.cover ? (
                        <img src={p.cover} alt={p.name} className="h-full w-full object-cover transition group-hover:scale-105" />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center text-zinc-500">
                          <Disc3 className="h-7 w-7" />
                        </div>
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-base font-bold text-white group-hover:text-accent transition">
                          {p.name}
                        </span>
                        <ArrowUpRight className="h-4 w-4 shrink-0 text-zinc-500 group-hover:text-accent transition" />
                      </div>

                      <div className="mt-1 flex items-center gap-2 text-xs text-zinc-400">
                        <span>{total} faixas</span>
                        <span>·</span>
                        <span className="text-emerald-400">{done} baixadas</span>
                      </div>
                    </div>
                  </div>

                  {/* Barra de progresso */}
                  <div className="mt-4 pt-3 border-t border-white/5">
                    <div className="flex items-center justify-between text-[11px] text-zinc-500 mb-1.5">
                      <span>Progresso</span>
                      <span className="font-semibold text-zinc-300">{pct}%</span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-accent to-accent-2 transition-all duration-300"
                        style={{ width: `${pct}%` }}
                      />
                    </div>

                    <div className="mt-3 flex items-center justify-end gap-1">
                      <button
                        onClick={(e) => handleReveal(p.id, e)}
                        className="btn-icon h-7 w-7"
                        title="Abrir pasta no Mac"
                      >
                        <Folder className="h-3.5 w-3.5" />
                      </button>
                      {done > 0 && (
                        <a
                          href={`/api/projects/${p.id}/zip`}
                          onClick={(e) => e.stopPropagation()}
                          className="btn-icon h-7 w-7"
                          title="Baixar ZIP com todas as faixas"
                        >
                          <Download className="h-3.5 w-3.5" />
                        </a>
                      )}
                      <button
                        onClick={(e) => handleDelete(p.id, p.name, e)}
                        className="btn-icon h-7 w-7 hover:text-rose-400"
                        title="Excluir projeto"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
