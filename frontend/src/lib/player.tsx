import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'

/** Player global de preview: toca um videoId por vez via /api/preview. */
type PlayerState = {
  current: string | null
  loading: boolean
  playing: boolean
  progress: number
  toggle: (videoId: string) => void
  stop: () => void
}

const Ctx = createContext<PlayerState | null>(null)

export function PlayerProvider({ children }: { children: ReactNode }) {
  const audio = useRef<HTMLAudioElement | null>(null)
  const [current, setCurrent] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const a = new Audio()
    a.preload = 'auto'
    a.onplaying = () => {
      setLoading(false)
      setPlaying(true)
    }
    a.onpause = () => setPlaying(false)
    a.onended = () => {
      setPlaying(false)
      setCurrent(null)
    }
    a.onerror = () => {
      setLoading(false)
      setPlaying(false)
    }
    a.ontimeupdate = () => setProgress(a.duration ? a.currentTime / a.duration : 0)
    audio.current = a
    return () => a.pause()
  }, [])

  const toggle = useCallback(
    (videoId: string) => {
      const a = audio.current!
      if (current === videoId) {
        if (a.paused) a.play()
        else a.pause()
        return
      }
      setCurrent(videoId)
      setLoading(true)
      setProgress(0)
      a.src = `/api/preview/${videoId}`
      a.play().catch(() => setLoading(false))
    },
    [current],
  )

  const stop = useCallback(() => {
    audio.current?.pause()
    setCurrent(null)
  }, [])

  return <Ctx.Provider value={{ current, loading, playing, progress, toggle, stop }}>{children}</Ctx.Provider>
}

export function usePlayer() {
  const c = useContext(Ctx)
  if (!c) throw new Error('PlayerProvider ausente')
  return c
}
