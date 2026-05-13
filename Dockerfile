# ── Slim Python base (saves ~4GB vs ubuntu + manual python) ──────────────────
FROM python:3.10-slim-bookworm

LABEL maintainer="QML-PLACE"

# ── Environment ───────────────────────────────────────────────────────────────
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99 \
    QT_QPA_PLATFORM=xcb \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ── LAYER 1: System packages (rarely changes → cached after first build) ──────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # EGL / OpenGL — required by PyQt6
    libegl1 libegl-mesa0 libgl1 libgl1-mesa-dri \
    libgles2 libgbm1 libglx-mesa0 libglx0 \
    # X11 / XCB — required by PyQt6 xcb platform plugin
    libx11-6 libxext6 libxrender1 libxrandr2 libxfixes3 libxi6 \
    libxcb1 libxcb-cursor0 libxcb-xinerama0 libxcb-shape0 \
    libxcb-util1 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-render-util0 libxcb-xkb1 libxkbcommon-x11-0 libxkbcommon0 \
    # Fonts / misc Qt deps
    libfontconfig1 libfreetype6 libdbus-1-3 libglib2.0-0 \
    # Virtual display + VNC
    xvfb x11vnc websockify novnc \
    # Utilities
    netcat-openbsd curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ── LAYER 2: PyQt6 wheels (rarely changes → cached) ──────────────────────────
RUN pip install --no-cache-dir \
    PyQt6==6.6.1 \
    PyQt6-sip==13.6.0 \
    PyQt6-Qt6==6.6.1

# ── LAYER 3: Heavy deps (changes only if requirements.txt changes) ────────────
WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── LAYER 4: App code (changes often → at the bottom, doesn't bust above) ─────
COPY . /workspace/
RUN mkdir -p /workspace/{designs,results,checkpoints,logs,configs}

# ── VNC password ──────────────────────────────────────────────────────────────
RUN mkdir -p /root/.vnc && \
    x11vnc -storepasswd qmlplace /root/.vnc/passwd 2>/dev/null || true

EXPOSE 6080 5900
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
