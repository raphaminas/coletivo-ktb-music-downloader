import { useState, useEffect } from 'react'
import { X, Check, Folder, Sparkles, AlertCircle, RefreshCw, Music2 } from 'lucide-react'
import { api, type Settings } from '../lib/api'
import { toast } from 'sonner'

export function SettingsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [saving, setSaving] = useState(false)
  const [checkingPremium, setCheckingPremium] = useState(false)
  const [premiumStatus, setPremiumStatus] = useState<{ ok: boolean; premium: boolean; message: string } | null>(null)
  const [chromeProfiles, setChromeProfiles] = useState<{ dir: string; name: string; email: string }[]>([])

  useEffect(() => {
    if (!open) return
    Promise.all([
      api.settings(),
      api.chromeProfiles().catch(() => ({ profiles: [] })),
    ])
      .then(([s, cp]) => {
        setSettings(s)
        setChromeProfiles(cp.profiles || [])
      })
      .catch((err) => toast.error('Falha ao carregar configurações: ' + (err as Error).message))
  }, [open])

  if (!open || !settings) return null

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.saveSettings(settings)
      toast.success('Configurações salvas!')
      onClose()
    } catch (e) {
      toast.error('Erro ao salvar: ' + (e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const handleTestPremium = async () => {
    setCheckingPremium(true)
    setPremiumStatus(null)
    try {
      // Salva antes de testar para usar o perfil selecionado
      await api.saveSettings(settings)
      const res = await api.checkPremium()
      setPremiumStatus(res)
      if (res.premium) {
        toast.success('YouTube Music Premium detectado (256kbps ativo)!')
      } else {
        toast.warning(res.message || 'Stream de 256kbps não encontrado.')
      }
    } catch (e) {
      setPremiumStatus({ ok: false, premium: false, message: (e as Error).message })
      toast.error('Erro ao verificar cookies: ' + (e as Error).message)
    } finally {
      setCheckingPremium(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl rounded-2xl border border-white/10 bg-[#0d0f15] p-6 shadow-2xl shadow-black/80">
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/10 text-accent">
              <Music2 className="h-4 w-4" />
            </div>
            <h2 className="text-lg font-bold text-white">Configurações de Download</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-zinc-400 hover:bg-white/10 hover:text-white transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-5 space-y-5 max-h-[72vh] overflow-y-auto pr-1">
          {/* Formato */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
              Formato de Saída (DJ)
            </label>
            <div className="grid grid-cols-3 gap-3">
              {[
                { id: 'mp3', label: 'MP3 320 CBR', desc: 'Compatibilidade total (CDJ/USB)' },
                { id: 'wav', label: 'WAV 16-bit', desc: 'Sem perdas 44.1kHz PCM' },
                { id: 'm4a', label: 'M4A 256 AAC', desc: 'Stream original sem transcode' },
              ].map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setSettings({ ...settings, format: f.id as any })}
                  className={`flex flex-col items-start rounded-xl border p-3 text-left transition ${
                    settings.format === f.id
                      ? 'border-accent bg-accent/10 text-white shadow-[0_0_15px_rgba(163,255,92,0.15)]'
                      : 'border-white/10 bg-white/[0.02] text-zinc-300 hover:bg-white/[0.05]'
                  }`}
                >
                  <span className="font-semibold text-sm flex items-center gap-1.5">
                    {f.label}
                    {settings.format === f.id && <Check className="h-3.5 w-3.5 text-accent" />}
                  </span>
                  <span className="mt-1 text-[11px] text-zinc-400 leading-tight">{f.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Cookies / Premium */}
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm font-semibold text-white flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-accent" />
                  YouTube Music Premium & Cookies
                </span>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Lê cookies do seu navegador para baixar o áudio em 256kbps reais
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Navegador</label>
                <select
                  className="input text-xs"
                  value={settings.cookies_browser}
                  onChange={(e) => setSettings({ ...settings, cookies_browser: e.target.value })}
                >
                  <option value="chrome">Google Chrome</option>
                  <option value="safari">Safari</option>
                  <option value="brave">Brave</option>
                  <option value="edge">Edge</option>
                  <option value="">Desativado (Sem cookies)</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-zinc-400 block mb-1">Perfil do Chrome</label>
                {chromeProfiles.length > 0 ? (
                  <select
                    className="input text-xs"
                    value={settings.cookies_profile}
                    onChange={(e) => setSettings({ ...settings, cookies_profile: e.target.value })}
                  >
                    {chromeProfiles.map((p) => (
                      <option key={p.dir} value={p.name}>
                        {p.name} {p.email ? `(${p.email})` : ''}
                      </option>
                    ))}
                    <option value="raphael">raphael (padrão)</option>
                  </select>
                ) : (
                  <input
                    className="input text-xs"
                    value={settings.cookies_profile}
                    onChange={(e) => setSettings({ ...settings, cookies_profile: e.target.value })}
                    placeholder="ex: raphael ou Profile 1"
                  />
                )}
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between">
              <button
                type="button"
                onClick={handleTestPremium}
                disabled={checkingPremium || !settings.cookies_browser}
                className="btn btn-ghost text-xs h-8"
              >
                <RefreshCw className={`h-3 w-3 ${checkingPremium ? 'animate-spin' : ''}`} />
                {checkingPremium ? 'Verificando...' : 'Testar conta Premium'}
              </button>

              {premiumStatus && (
                <div className={`text-xs flex items-center gap-1.5 ${premiumStatus.premium ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {premiumStatus.premium ? <Check className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                  <span>{premiumStatus.message}</span>
                </div>
              )}
            </div>
          </div>

          {/* Pasta de saída */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
              Pasta de Destino
            </label>
            <div className="relative">
              <Folder className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
              <input
                className="input pl-9 text-xs"
                value={settings.output_dir}
                onChange={(e) => setSettings({ ...settings, output_dir: e.target.value })}
                placeholder="~/Music/DJ Downloader"
              />
            </div>
            <p className="mt-1 text-[11px] text-zinc-500">
              Dica: você pode apontar para a pasta do <strong>Google Drive para Desktop</strong> para sincronizar automaticamente na nuvem.
            </p>
          </div>

          {/* Nome do arquivo */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                Padrão de Nome
              </label>
              <input
                className="input text-xs"
                value={settings.filename_pattern}
                onChange={(e) => setSettings({ ...settings, filename_pattern: e.target.value })}
                placeholder="{artist} - {title}"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                Downloads Simultâneos
              </label>
              <select
                className="input text-xs"
                value={settings.concurrency}
                onChange={(e) => setSettings({ ...settings, concurrency: Number(e.target.value) })}
              >
                <option value={1}>1 faixa por vez</option>
                <option value={2}>2 faixas simultâneas (recomendado)</option>
                <option value={3}>3 faixas simultâneas</option>
                <option value={4}>4 faixas simultâneas</option>
              </select>
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3 pt-4 border-t border-white/10">
          <button type="button" onClick={onClose} className="btn btn-ghost text-xs">
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="btn btn-primary text-xs"
          >
            {saving ? 'Salvando...' : 'Salvar Alterações'}
          </button>
        </div>
      </div>
    </div>
  )
}
