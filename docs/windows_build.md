# 🪟 DJ Downloader para Windows 11 / 10

Este documento explica como o instalador executável para Windows foi estruturado para ser **seguro, moderno e simples para qualquer usuário leigo**, sem exigir comandos no terminal ou instalação manual de ferramentas.

---

## 🛡️ Pilares de Segurança & Compatibilidade Windows 11

1. **Instalação no Perfil do Usuário (`PrivilegesRequired=lowest`):**
   - Instala em `%LOCALAPPDATA%\Programs\DJ Downloader`.
   - **Não exige privilégios de Administrador** nem dispara pop-ups do UAC (User Account Control).
   - O aplicativo não toca em pastas protegidas do sistema (`System32` ou `Program Files`).
2. **Interface Nativa via WebView2:**
   - O Windows 11 já vem de fábrica com o componente **Microsoft Edge WebView2**.
   - O aplicativo abre como uma janela desktop nativa, rápida e elegante, sem a lentidão ou consumo excessivo de memória do Electron.
3. **Binários Embutidos (Zero Dependências Externas):**
   - O instalador já inclui `ffmpeg.exe` e `ffprobe.exe` embutidos. O usuário não precisa instalar nem configurar variáveis de ambiente.
4. **Desinstalador Limpo:**
   - Registrado oficialmente no Windows 11 (`Configurações > Aplicativos > Aplicativos Instalados`), removendo todos os arquivos e atalhos sem deixar lixo no registro.

---

## 🚀 Opção 1: Compilar Automaticamente via Nuvem (GitHub Actions)

Como você está usando um Mac, o jeito mais prático de gerar o `.exe` para outros usuários sem precisar de uma máquina Windows é usar o GitHub Actions que configuramos:

1. Suba o projeto para um repositório no seu GitHub:
   ```bash
   git add .
   git commit -m "feat: suporte a instalador do Windows 11"
   git push origin main
   ```
2. No seu repositório no GitHub:
   - Vá na aba **Actions**.
   - Selecione o workflow **"Build Windows 11 Installer"**.
   - Clique em **"Run workflow"**.
3. O GitHub irá iniciar uma máquina virtual Windows 11 limpa, compilar tudo e disponibilizar o arquivo `DJ-Downloader-Setup-1.0.0.exe` pronto para download na seção **Artifacts** (ou **Releases** ao criar uma tag `v1.0.0`).

---

## 💻 Opção 2: Compilar Diretamente em um Computador Windows

Se você (ou um colega) tiver um PC com Windows:

1. Baixe ou clone a pasta do projeto.
2. Certifique-se de ter instalado:
   - [Python 3.10+](https://www.python.org/downloads/) (marque a caixa *"Add Python to PATH"* na instalação).
   - [Node.js LTS](https://nodejs.org/).
   - [Inno Setup 6](https://jrsoftware.org/isdl.php) (opcional, para gerar o `.exe` Setup único).
3. Dê dois cliques no arquivo:
   ```cmd
   windows\build_windows.bat
   ```
4. O script fará tudo sozinho:
   - Compila o frontend React.
   - Baixa os binários oficiais do FFmpeg para Windows.
   - Empacota o executável com PyInstaller.
   - Gera o instalador final em `dist-installer\DJ-Downloader-Setup-1.0.0.exe`.

---

## 🎧 Experiência do Usuário Final no Windows

1. O usuário dá dois cliques no `DJ-Downloader-Setup-1.0.0.exe`.
2. O assistente em Português instala o programa e cria o atalho no Menu Iniciar e na Área de Trabalho com o ícone do DJ Downloader.
3. Ao abrir o aplicativo, uma janela moderna do Windows 11 surge pronta para colar links do Spotify e baixar as faixas em MP3 320 ou WAV.
