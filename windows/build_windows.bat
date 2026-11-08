@echo off
setlocal enabledelayedexpansion

echo =======================================================
echo   DJ Downloader - Gerador de Instalador para Windows
echo =======================================================
echo.

cd /d "%~dp0\.."

:: 1. Verifica Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERRO] Python nao encontrado no PATH. Instale o Python 3.10+ do site python.org.
    pause
    exit /b 1
)

:: 2. Verifica Node.js
where npm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERRO] Node.js/npm nao encontrado no PATH. Instale o Node.js 18+ do site nodejs.org.
    pause
    exit /b 1
)

:: 3. Instala dependencias do Frontend e compila
echo [1/5] Compilando Frontend React...
cd frontend
call npm install --no-audit --no-fund
call npm run build
if %ERRORLEVEL% neq 0 (
    echo [ERRO] Falha ao compilar o frontend.
    pause
    exit /b 1
)
cd ..

:: 4. Instala dependencias do Python
echo [2/5] Instalando dependencias Python...
python -m pip install -q --upgrade pip
python -m pip install -q -r backend/requirements.txt
python -m pip install -q pyinstaller pywebview

:: 5. Garante ffmpeg e ffprobe em windows/bin
echo [3/5] Verificando ffmpeg para Windows...
if not exist "windows\bin\ffmpeg.exe" (
    echo     Baixando ffmpeg essencial para Windows 64-bit...
    if not exist "windows\bin" mkdir "windows\bin"
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' -OutFile 'windows\ffmpeg.zip'"
    powershell -Command "Expand-Archive -Path 'windows\ffmpeg.zip' -DestinationPath 'windows\ffmpeg_temp' -Force"
    for /d %%D in (windows\ffmpeg_temp\ffmpeg-*) do (
        copy /y "%%D\bin\ffmpeg.exe" "windows\bin\" >nul
        copy /y "%%D\bin\ffprobe.exe" "windows\bin\" >nul
    )
    rmdir /s /q "windows\ffmpeg_temp"
    del /q "windows\ffmpeg.zip"
    echo     ffmpeg e ffprobe instalados com sucesso em windows\bin!
) else (
    echo     ffmpeg ja presente em windows\bin.
)

:: 6. Executa PyInstaller
echo [4/5] Empacotando aplicacao com PyInstaller...
python -m PyInstaller --clean -y windows/dj-downloader.spec
if %ERRORLEVEL% neq 0 (
    echo [ERRO] Falha no empacotamento com PyInstaller.
    pause
    exit /b 1
)

:: 7. Compila Instalador com Inno Setup se disponivel
echo [5/5] Gerando Instalador Windows...
set "ISCC_PATH="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_PATH=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_PATH=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if defined ISCC_PATH (
    echo     Inno Setup encontrado: "!ISCC_PATH!"
    "!ISCC_PATH!" windows\installer.iss
    echo.
    echo =======================================================
    echo   SUCESSO! Instalador gerado em:
    echo   dist-installer\DJ-Downloader-Setup-1.0.0.exe
    echo =======================================================
) else (
    echo.
    echo [AVISO] Inno Setup 6 nao encontrado para gerar o arquivo .exe de instalacao.
    echo Porem, a pasta portatil do aplicativo foi gerada com sucesso em:
    echo dist\DJ Downloader\DJ Downloader.exe
    echo.
    echo Para gerar o instalador Setup unico, instale o Inno Setup 6 gratuito em:
    echo https://jrsoftware.org/isdl.php e execute este script novamente.
)

echo.
pause
