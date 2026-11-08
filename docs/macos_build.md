# 🍎 DJ Downloader para macOS

Este documento explica como o aplicativo nativo para **macOS** (`DJ Downloader.app`) e seu instalador oficial em formato de Imagem de Disco (`DJ-Downloader-macOS.dmg`) foram configurados.

---

## 🛡️ Características do App para macOS

1. **Interface Nativa via Cocoa / WebKit (WKWebView):**
   - O aplicativo roda como um app nativo de Mac com cantos arredondados, botões de fechar/minimizar nativos (traffic lights), suporte ao Dark Mode do sistema e ícone próprio no Dock.
2. **Zero Dependências do Terminal (FFmpeg Embutido):**
   - O pacote `.app` já inclui os binários estáticos do **FFmpeg** e **FFprobe** para Apple Silicon (M1/M2/M3/M4) e Intel.
   - O usuário não precisa ter Homebrew, Python ou Node instalados na máquina.
3. **Instalação Padrão do Mac (Arrastar para Applications):**
   - O arquivo `.dmg` abre a janela clássica onde basta arrastar o ícone do **DJ Downloader** para a pasta **Applications (Aplicativos)**.

---

## 💻 Compilação Local (No seu próprio Mac)

Basta rodar no terminal:

```bash
./macos/build_macos.sh
```

O script:
1. Compila o frontend React.
2. Baixa e configura o FFmpeg estático nativo.
3. Empacota com PyInstaller criando `dist/DJ Downloader.app`.
4. Aplica assinatura local ad-hoc para aprovação do macOS Gatekeeper.
5. Gera o instalador `.dmg` em `dist-installer/DJ-Downloader-macOS.dmg`.

---

## 🚀 Compilação Automática na Nuvem (GitHub Actions)

O repositório já conta com a automação `.github/workflows/build-macos.yml`:

- A cada push na branch `main` ou criação de tag de versão (ex.: `v1.0.0`), o GitHub sobe uma máquina virtual **macOS Apple Silicon** limpa, compila o `.app`, gera o `.dmg` e disponibiliza para download na seção **Artifacts** ou **Releases** do repositório.
