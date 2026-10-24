import clsx from 'clsx'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown, ExternalLink, Link2, Search, Trash2, Check } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import type { Candidate, Track } from '../lib/api'
import { api, fmtDuration, trackCover } from '../lib/api'
import { removeTrack } from '../lib/store'
import { DownloadCell } from './DownloadCell'
import { ConfidenceBadge, CoverPlay, KindBadge, Pill } from './ui'

function durDiff(src?: number | null, c?: number | null) {
  if (!src || !c) return null
  const d = c - src
  if (Math.abs(d) <= 3) return null
  return (
    <span className={clsx('text-[11px]', Math.abs(d) > 15 ? 'text-rose-300' : 'text-amber-300')}>
      {d > 0 ? '+' : ''}
      {d}s
    </span>
  )
}

export function TrackRow({ track, index }: { track: Track; index: number }) {
  const [open, setOpen] = useState(false)
  const sel = track.selected
  const extended = track.alternatives.filter((a) => a.alt_kind === 'extended')
  const studio = track.alternatives.find((a) => a.alt_kind === 'studio')

  return (
    <motion.div
      layout="position"
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: Math.min(index * 0.015, 0.4) }}
      className={clsx(
        'group rounded-2xl border transition',
        open ? 'border-white/10 bg-white/[0.04]' : 'border-transparent hover:bg-white/[0.03]',
      )}
    >
      <div className="grid grid-cols-[28px_minmax(0,1.2fr)_minmax(0,1.3fr)_90px_190px_36px] items-center gap-4 px-3 py-2.5">
        <span className="text-right text-xs tabular-nums text-zinc-500">{index + 1}</span>

        {/* origem */}
        <div className="flex min-w-0 items-center gap-3">
          <CoverPlay src={trackCover(track)} videoId={sel?.video_id} />
          <div className="min-w-0">
            <div className="truncate font-medium text-zinc-100">{track.source.title}</div>
            <div className="truncate text-sm text-zinc-400">
              {track.source.artists.join(', ')}
              <span className="ml-2 text-zinc-600">{fmtDuration(track.source.duration)}</span>
            </div>
          </div>
        </div>

        {/* versão escolhida */}
        <button className="min-w-0 text-left" onClick={() => setOpen((o) => !o)}>
          {sel ? (
            <>
              <div className="flex items-center gap-2">
                <span className="truncate text-sm text-zinc-200">{sel.title}</span>
                <KindBadge c={sel} />
              </div>
              <div className="mt-0.5 flex items-center gap-2 truncate text-xs text-zinc-500">
                <span className="truncate">{sel.artists.join(', ')}</span>
                <span>· {fmtDuration(sel.duration)}</span>
                {durDiff(track.source.duration, sel.duration)}
                {!sel.alt_kind && extended.length > 0 && (
                  <Pill tone="purple" className="ml-1">
                    +{extended.length} extended
                  </Pill>
                )}
                {!sel.alt_kind && studio && <Pill tone="blue">estúdio disponível</Pill>}
              </div>
            </>
          ) : track.status === 'matching' ? (
            <div className="h-8 w-2/3 animate-pulse rounded-lg bg-white/5" />
          ) : (
            <span className="text-sm text-rose-300">Nenhum resultado. Clique para buscar manualmente.</span>
          )}
        </button>

        <div>
          <ConfidenceBadge track={track} />
        </div>

        <div className="flex justify-end">
          <DownloadCell track={track} />
        </div>

        <button className="btn-icon" onClick={() => setOpen((o) => !o)} title="Revisar versões">
          <ChevronDown className={clsx('h-4 w-4 transition', open && 'rotate-180')} />
        </button>
      </div>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <ReviewPanel track={track} onDone={() => setOpen(false)} />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function ReviewPanel({ track, onDone }: { track: Track; onDone: () => void }) {
  const [url, setUrl] = useState('')
  const [query, setQuery] = useState(`${track.source.artists.slice(0, 2).join(' ')} ${track.source.title}`)
  const [busy, setBusy] = useState(false)

  const choose = async (c: Candidate) => {
    try {
      await api.selectCandidate(track.id, c.video_id)
      toast.success('Versão escolhida')
      onDone()
    } catch (e) {
      toast.error((e as Error).message)
    }
  }
  const useUrl = async () => {
    if (!url.trim()) return
    setBusy(true)
    try {
      await api.setUrl(track.id, url.trim())
      setUrl('')
      toast.success('Link aplicado')
      onDone()
    } catch (e) {
      toast.error((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  const search = async () => {
    await api.rematch(track.id, query)
  }
  const del = async () => {
    await api.deleteTrack(track.id)
    removeTrack(track.id)
  }

  const groups: { title: string; items: Candidate[] }[] = [
    { title: 'Sugestões para DJ', items: track.alternatives },
    { title: 'Candidatos', items: track.candidates },
  ]

  return (
    <div className="space-y-4 border-t border-white/5 px-4 pb-4 pt-3 pl-[52px]">
      {groups.map(
        (g) =>
          g.items.length > 0 && (
            <div key={g.title}>
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-zinc-500">{g.title}</div>
              <div className="grid gap-1.5 md:grid-cols-2">
                {g.items.map((c) => {
                  const active = track.selected?.video_id === c.video_id
                  return (
                    <div
                      key={c.video_id + (c.alt_kind ?? '')}
                      className={clsx(
                        'flex items-center gap-3 rounded-xl border p-2 transition',
                        active ? 'border-accent/40 bg-accent/5' : 'border-white/5 bg-black/20 hover:border-white/15',
                      )}
                    >
                      <CoverPlay src={c.thumbnail} videoId={c.video_id} size={40} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="truncate text-sm">{c.title}</span>
                        </div>
                        <div className="flex items-center gap-2 truncate text-xs text-zinc-500">
                          <span className="truncate">{c.artists.join(', ')}</span>
                          <span>· {fmtDuration(c.duration)}</span>
                          {durDiff(track.source.duration, c.duration)}
                        </div>
                      </div>
                      <KindBadge c={c} />
                      {!c.alt_kind && (
                        <span className="w-9 text-right text-[11px] tabular-nums text-zinc-500">
                          {Math.round(c.score * 100)}
                        </span>
                      )}
                      <a
                        className="btn-icon"
                        href={`https://music.youtube.com/watch?v=${c.video_id}`}
                        target="_blank"
                        rel="noreferrer"
                        title="Abrir no YouTube Music"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                      {active ? (
                        <span className="btn-icon text-accent">
                          <Check className="h-4 w-4" />
                        </span>
                      ) : (
                        <button className="btn btn-ghost h-7 px-2.5 text-xs" onClick={() => choose(c)}>
                          Usar
                        </button>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ),
      )}

      <div className="grid gap-2 md:grid-cols-2">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
            <input
              className="input pl-9"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && search()}
              placeholder="Buscar outra versão no YT Music"
            />
          </div>
          <button className="btn btn-ghost" onClick={search}>
            Buscar
          </button>
        </div>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Link2 className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
            <input
              className="input pl-9"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && useUrl()}
              placeholder="Colar link do YouTube / YT Music"
            />
          </div>
          <button className="btn btn-ghost" onClick={useUrl} disabled={busy}>
            Usar link
          </button>
        </div>
      </div>
      <div className="flex justify-end">
        <button className="btn h-8 px-3 text-xs text-zinc-500 hover:text-rose-300" onClick={del}>
          <Trash2 className="h-3.5 w-3.5" /> Remover da lista
        </button>
      </div>
    </div>
  )
}
