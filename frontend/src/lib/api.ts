export type Candidate = {
  video_id: string
  title: string
  artists: string[]
  album?: string | null
  duration?: number | null
  thumbnail?: string | null
  kind: 'song' | 'video'
  video_type?: string
  score: number
  tags: string[]
  version?: string | null
  alt_kind?: 'extended' | 'studio'
  alt_label?: string
  manual?: boolean
}

export type Download = {
  status: 'idle' | 'queued' | 'downloading' | 'processing' | 'done' | 'error'
  progress?: number
  speed?: number | null
  eta?: number | null
  path?: string
  format?: string
  source_abr?: number | null
  source_format?: string
  file_bitrate?: number | null
  quality_ok?: boolean
  used_cookies?: boolean
  warning?: string | null
  error?: string | null
  from_cache?: boolean
}

export type Track = {
  id: string
  project_id: string
  origin: 'spotify' | 'youtube' | 'text'
  source: {
    title: string
    artists: string[]
    duration?: number | null
    album?: string | null
    cover?: string | null
    cover_fallback?: string | null
    spotify_id?: string
    year?: string | null
  }
  status: 'matching' | 'matched' | 'not_found' | 'error'
  candidates: Candidate[]
  alternatives: Candidate[]
  selected: Candidate | null
  confidence: 'high' | 'medium' | 'low' | null
  user_confirmed?: boolean
  download: Download
  error?: string
}

export type ProjectMeta = {
  id: string
  name: string
  kind: 'playlist' | 'album' | 'list' | 'singles'
  source_url?: string | null
  cover?: string | null
  created_at: number
  track_count?: number
  done_count?: number
}

export type Project = ProjectMeta & { tracks: Track[] }

export type Settings = {
  format: 'mp3' | 'wav' | 'm4a'
  output_dir: string
  cookies_browser: string
  cookies_profile: string
  filename_pattern: string
  min_bitrate: number
  concurrency: number
}

async function req<T>(method: string, url: string, body?: unknown): Promise<T> {
  const r = await fetch(url, {
    method,
    headers: body ? { 'content-type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!r.ok) {
    let msg = `Erro ${r.status}`
    try {
      const j = await r.json()
      msg = j.detail || msg
    } catch {
      /* ignore */
    }
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  }
  return r.json()
}

export const api = {
  resolve: (input: string, project_id?: string) =>
    req<{ project_id: string; kind: string; count: number; truncated?: boolean; track_ids?: string[] }>(
      'POST', '/api/resolve', { input, project_id },
    ),
  projects: () => req<ProjectMeta[]>('GET', '/api/projects'),
  project: (id: string) => req<Project>('GET', `/api/projects/${id}`),
  renameProject: (id: string, name: string) => req<Project>('PATCH', `/api/projects/${id}`, { name }),
  deleteProject: (id: string) => req('DELETE', `/api/projects/${id}`),
  reveal: (id: string) => req('POST', `/api/projects/${id}/reveal`),
  selectCandidate: (tid: string, video_id: string) => req<Track>('PATCH', `/api/tracks/${tid}`, { video_id }),
  setUrl: (tid: string, url: string) => req<Track>('PATCH', `/api/tracks/${tid}`, { url }),
  rematch: (tid: string, query?: string) => req('POST', `/api/tracks/${tid}/rematch`, { query }),
  deleteTrack: (tid: string) => req('DELETE', `/api/tracks/${tid}`),
  download: (body: { track_ids?: string[]; project_id?: string; include_low?: boolean; redownload?: boolean }) =>
    req<{ queued: number }>('POST', '/api/download', body),
  settings: () => req<Settings>('GET', '/api/settings'),
  saveSettings: (s: Partial<Settings>) => req<Settings>('PUT', '/api/settings', s),
  chromeProfiles: () =>
    req<{ profiles: { dir: string; name: string; email: string }[]; resolved: string | null }>(
      'GET', '/api/chrome-profiles',
    ),
  checkPremium: () =>
    req<{ ok: boolean; premium: boolean; message: string; profile?: string }>('POST', '/api/check-premium'),
  health: () => req<{ ok: boolean; yt_dlp: string; ffmpeg: boolean; deno: boolean }>('GET', '/api/health'),
}

export const fmtDuration = (s?: number | null) => {
  if (!s && s !== 0) return '–'
  const m = Math.floor(s / 60)
  const r = Math.round(s % 60)
  return `${m}:${String(r).padStart(2, '0')}`
}

export const trackCover = (t: Track) =>
  t.source.cover || t.selected?.thumbnail || t.source.cover_fallback || null
