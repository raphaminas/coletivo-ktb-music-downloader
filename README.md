# 🎧 DJ Downloader

Aplicação local para DJs baixarem playlists do Spotify e faixas avulsas com a melhor qualidade de áudio do **YouTube Music (até 256kbps com conta Premium)**, metadados e tags ID3 completas com capa em alta resolução.

---

## ⚡ Início Rápido

Para iniciar a aplicação completa:

```bash
./start.sh
```

O comando irá:
1. Verificar e instalar dependências do Python e Node (se necessário).
2. Iniciar o servidor e abrir o navegador automaticamente em `http://localhost:8000`.

Para rodar em modo de desenvolvimento (com Hot Reload):
```bash
./start.sh --dev
```

---

## 🚀 Principais Funcionalidades

- **Múltiplas formas de importar:**
  - Link de playlist pública ou álbum do Spotify (`https://open.spotify.com/playlist/...`).
  - Link de faixa única do Spotify ou YouTube / YouTube Music.
  - Copiar e colar lista do Spotify Desktop (`Cmd+A` -> `Cmd+C`).
  - Digitar ou colar texto livre (ex.: `Daft Punk - One More Time` ou listas com múltiplas linhas).
- **Motor de Match Inteligente:**
  - Busca direta no catálogo oficial do **YouTube Music** (priorizando faixas oficiais "Topic").
  - Pontuação refinada por similaridade de título, artistas e duração (±3s).
  - Detecção automática de versões ao vivo, acústicas, remixes e penalidade para versões não oficiais (covers, karaokê, sped up).
- **Sugestões para DJ:**
  - Sugere versões **Extended Mix / Club Mix** oficiais automaticamente.
  - Sugere **Versões de Estúdio** caso a música da playlist seja ao vivo.
- **Qualidade Real (sem upscaling falso):**
  - **YouTube Music Premium:** lê os cookies do seu navegador (configurado para **Google Chrome**, perfil `raphael`) para acessar o stream oficial de 256kbps AAC (itag 141).
  - Medição do bitrate real de cada arquivo com `ffprobe`. Alerta visual caso o áudio original fique abaixo de 192kbps (ex.: quando baixado sem conta Premium logada).
- **Formatos de Saída:**
  - **MP3 320kbps CBR** (compatibilidade total com CDJs, mixers e pen-drives).
  - **WAV 16-bit 44.1kHz** (PCM sem perdas).
  - **M4A 256kbps AAC** (cópia direta do stream original sem nenhuma perda por recompressão).
- **Download em lote & ZIP:**
  - Fila com progresso em tempo real via WebSocket.
  - Botão de **Baixar Todas** as faixas confirmadas.
  - Exportação direta de todas as faixas em um arquivo `.zip`.
  - Botão para abrir a pasta de destino diretamente no **macOS Finder**.

---

## 🛠️ Arquitetura do Projeto

```
dj-downloader/
├── backend/
│   ├── app/
│   │   ├── main.py            # API FastAPI, WebSocket e servidor SPA
│   │   ├── sources/spotify.py # Leitor de playlists/faixas do Spotify
│   │   ├── matching/engine.py # Motor de busca, scoring e sugestões Extended/Studio
│   │   ├── download/          # Fila de downloads, yt-dlp, verificação ffprobe
│   │   ├── tagging.py         # Gravação de tags e capas com mutagen
│   │   └── db.py              # Banco SQLite para projetos, cache e histórico
│   └── requirements.txt
├── frontend/                  # React 19 + TypeScript + Vite + Tailwind CSS + Framer Motion
├── docs/                      # Proposta de arquitetura
└── start.sh                   # Script único de execução
```

---

## ⚙️ Configurações & Google Drive

Você pode acessar o menu **Configurações** na barra superior da aplicação para:
- Escolher entre **MP3 320**, **WAV** ou **M4A 256**.
- Alterar o perfil do Chrome e testar o status da conta Premium com um clique.
- Alterar a pasta de saída. **Dica:** aponte para a sua pasta do **Google Drive para Desktop** (ex.: `~/Google Drive/Meu Drive/DJ/`) para sincronização automática em nuvem.
