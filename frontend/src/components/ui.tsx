import clsx from 'clsx'
import { motion } from 'framer-motion'
import { Pause, Play, Loader2 } from 'lucide-react'
import type { Candidate, Track } from '../lib/api'
import { usePlayer } from '../lib/player'

export function ConfidenceBadge({ track }: { track: Track }) {
  if (track.status === 'matching')
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-white/5 px-2 py-0.5 text-[11px] text-zinc-400">
        <Loader2 className="h-3 w-3 animate-spin" /> buscando
      </span>
    )
  if (track.status === 'not_found' || track.status === 'error')
    return <Pill tone="red">não encontrada</Pill>
  if (track.user_confirmed) return <Pill tone="green">confirmada</Pill>
  const c = track.confidence
  if (c === 'high') return <Pill tone="green">alta</Pill>
  if (c === 'medium') return <Pill tone="yellow">revisar</Pill>
  return <Pill tone="red">baixa</Pill>
}

export function Pill({
  tone,
  children,
  className,
}: {
  tone: 'green' | 'yellow' | 'red' | 'blue' | 'zinc' | 'purple'
  children: React.ReactNode
  className?: string
}) {
  const tones = {
    green: 'bg-emerald-400/10 text-emerald-300 ring-emerald-400/20',
    yellow: 'bg-amber-400/10 text-amber-300 ring-amber-400/20',
    red: 'bg-rose-500/10 text-rose-300 ring-rose-400/20',
    blue: 'bg-sky-400/10 text-sky-300 ring-sky-400/20',
    purple: 'bg-fuchsia-400/10 text-fuchsia-300 ring-fuchsia-400/20',
    zinc: 'bg-white/5 text-zinc-400 ring-white/10',
  }
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset',
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}

export function KindBadge({ c }: { c: Candidate }) {
  if (c.alt_kind === 'extended') return <Pill tone="purple">🎛️ {c.alt_label || 'Extended'}</Pill>
  if (c.alt_kind === 'studio') return <Pill tone="blue">🎙️ Estúdio</Pill>
  return c.kind === 'song' ? <Pill tone="zinc">Oficial</Pill> : <Pill tone="zinc">Vídeo</Pill>
}

export function Equalizer({ className }: { className?: string }) {
  return (
    <span className={clsx('flex h-3.5 items-end gap-[2px]', className)}>
      {[0, 0.2, 0.4, 0.1].map((d, i) => (
        <span key={i} className="eq-bar w-[3px] rounded-sm bg-accent" style={{ height: '100%', animationDelay: `${d}s` }} />
      ))}
    </span>
  )
}

/** Capa com botão de preview por cima. */
export function CoverPlay({ src, videoId, size = 44 }: { src?: string | null; videoId?: string | null; size?: number }) {
  const p = usePlayer()
  const active = videoId && p.current === videoId
  return (
    <button
      type="button"
      disabled={!videoId}
      onClick={() => videoId && p.toggle(videoId)}
      className="group relative shrink-0 overflow-hidden rounded-lg bg-white/5"
      style={{ width: size, height: size }}
      title="Ouvir prévia"
    >
      {src ? <img src={src} alt="" className="h-full w-full object-cover" loading="lazy" /> : null}
      <span
        className={clsx(
          'absolute inset-0 flex items-center justify-center bg-black/55 transition',
          active ? 'opacity-100' : 'opacity-0 group-hover:opacity-100',
        )}
      >
        {active && p.loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : active && p.playing ? (
          <Pause className="h-4 w-4" fill="currentColor" />
        ) : (
          <Play className="h-4 w-4" fill="currentColor" />
        )}
      </span>
      {active && (
        <motion.span
          className="absolute bottom-0 left-0 h-[3px] bg-accent"
          style={{ width: `${p.progress * 100}%` }}
        />
      )}
    </button>
  )
}

export function ProgressBar({ value, className }: { value: number; className?: string }) {
  return (
    <div className={clsx('h-1.5 w-full overflow-hidden rounded-full bg-white/10', className)}>
      <motion.div
        className="h-full rounded-full bg-gradient-to-r from-accent to-accent-2"
        animate={{ width: `${Math.max(2, Math.min(100, value))}%` }}
        transition={{ ease: 'easeOut', duration: 0.3 }}
      />
    </div>
  )
}
