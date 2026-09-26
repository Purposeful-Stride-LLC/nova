# Resource notes ? OG tentacle (living)
Updated: 2026-09-22T11:42:02Z

## Mail / beacon
- Ports from TUF: {"41776": "open", "41777": "open", "22": "open"}
- Tentacle: TCP 41776 beacon + TCP 41777 jobs
- Hub: nova/hearthbeat.py

## Live snapshot
- health: {"ok": true, "abilities": ["cpu_llm", "shell", "net", "fs_map", "cam", "mic"], "proto": "tcp"}
- which: {"python3": "/usr/bin/python3", "ffmpeg": "/usr/bin/ffmpeg", "curl": "/usr/bin/curl", "git": "", "ollama": "/usr/local/bin/ollama", "freecad": "/usr/bin/freecad"}
- apt n_pkgs: 2377
- apt interesting: ["audacity", "audacity-data", "cheese", "cheese-common", "curl", "ffmpeg", "freecad", "freecad-common", "freecad-python3", "imagemagick-6-common", "libcheese-gtk25:amd64", "libcheese8:amd64", "libcurl3-gnutls:amd64", "libcurl4:amd64", "libfreecad-python3-0.19", "libgit2-1.1:amd64", "libgnuradio-digital3.10.1:amd64", "libpython3-dev:amd64", "libpython3-stdlib:amd64", "libpython3.10:amd64", "libpython3.10-dev:amd64", "libpython3.10-minimal:amd64", "libpython3.10-stdlib:amd64", "libqgispython3.44.7", "libreoffice-base-core", "libreoffice-calc", "libreoffice-common", "libreoffice-core", "libreoffice-draw", "libreoffice-gnome", "libreoffice-gtk3", "libreoffice-help-common", "libreoffice-help-en-us", "libreoffice-impress", "libreoffice-math", "libreoffice-ogltrans", "libreoffice-pdfimport", "libreoffice-style-breeze", "libreoffice-style-colibre", "libreoffice-style-elementary"]

## Already on disk
- OG_PROFILE, OG_ACQ raw, OG_CODESUM_pg, PLAN_AFTER_INVENTORY
- Prior outbox drills: discover/map/ffmpeg/freecad/curl

## Parallel lanes
- Aurelius: STEP_AVATAR_PYTHON_BUILD.txt
- Cassius: Qwen-image + NOVA paint hook
- Varro: hearthbeat + resource notes