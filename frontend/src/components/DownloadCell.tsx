import clsx from 'clsx'
import { AlertTriangle, CheckCircle2, Download, FileAudio, Loader2, RotateCcw } from 'lucide-react'
import type { Track } from '../lib/api'
import { api } from '../lib/api'
import { Pill, ProgressBar } from './ui'
import { toast } from 'sonner'

export function QualityBadge({ track }: { track: Track }) {
  const d = track.download
  if (d.status !== 'done') return null
  const abr = d.source_abr
  const ok = d.quality_ok
  return (
    <span
      title={`Fonte: ${abr ?? '?'}kbps (${d.source_format ?? ''}) · Arquivo: ${d.file_bitrate ?? '?'}kbps ${d.format?.toUpperCase() ?? ''}${
        d.warning ? `\n${d.warning}` : ''
      }`}
    >
      <Pill tone={ok ? 'green' : 'red'}>
        {ok ? '🟢' : '🔴'} {abr ? `${abr}k` : '?'}
        <span className="opacity-60">→ {d.format?.toUpperCase()}</span>
      </Pill>
    </span>
  )
}

export function DownloadCell({ track }: { track: Track }) {
  const d = track.download
  const canDownload = !!track.selected && track.status !== 'matching'

  const start = async () => {
    try {
      await api.download({ track_ids: [track.id] })
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  if (d.status === 'queued')
    return (
      <div className="flex items-center gap-2 text-xs text-zinc-400">
        <Loader2 className="h-3.5 w-3.5 animate-spin" /> na fila
      </div>
    )
  if (d.status === 'downloading' || d.status === 'processing')
    return (
      <div className="w-full min-w-28">
        <div className="mb-1 flex justify-between text-[11px] text-zinc-400">
          <span>{d.status === 'processing' ? 'convertendo…' : 'baixando'}</span>
          <span>{d.status === 'processing' ? '' : `${Math.round(d.progress ?? 0)}%`}</span>
        </div>
        <ProgressBar value={d.status === 'processing' ? 100 : d.progress ?? 0} />
      </div>
    )
  if (d.status === 'done')
    return (
      <div className="flex items-center gap-1.5">
        <QualityBadge track={track} />
        <a className="btn-icon" href={`/api/tracks/${track.id}/file`} title="Salvar arquivo">
          <FileAudio className="h-4 w-4" />
        </a>
        <button className="btn-icon" title="Baixar de novo" onClick={start}>
          <RotateCcw className="h-3.5 w-3.5" />
        </button>
      </div>
    )
  if (d.status === 'error')
    return (
      <div className="flex items-center gap-1.5">
        <span title={d.error ?? ''} className="flex items-center gap-1 text-xs text-rose-300">
          <AlertTriangle className="h-3.5 w-3.5" /> erro
        </span>
        <button className="btn-icon" title={`Tentar de novo\n${d.error ?? ''}`} onClick={start}>
          <RotateCcw className="h-3.5 w-3.5" />
        </button>
      </div>
    )
  return (
    <button
      className={clsx('btn btn-ghost h-8 px-3 text-xs', !canDownload && 'opacity-40')}
      disabled={!canDownload}
      onClick={start}
    >
      <Download className="h-3.5 w-3.5" /> Baixar
    </button>
  )
}

export function DoneIcon() {
  return <CheckCircle2 className="h-4 w-4 text-emerald-400" />
}
