#!/bin/bash
# ── QML·PLACE Docker Entrypoint ───────────────────────────────────────────────
set -e

DISPLAY_NUM=${DISPLAY:-:99}
VNC_PORT=${VNC_PORT:-5900}
NOVNC_PORT=${NOVNC_PORT:-6080}
RESOLUTION="${SCREEN_WIDTH:-1920}x${SCREEN_HEIGHT:-1080}x${SCREEN_DEPTH:-24}"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║          QML·PLACE — VLSI Placement Engine          ║"
echo "║              OpenROAD Sky130 / CA234                ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 1. Start Xvfb (virtual framebuffer display) ───────────────────────────────
echo "[STARTUP] Starting virtual display Xvfb on ${DISPLAY_NUM} @ ${RESOLUTION}"
rm -f /tmp/.X99-lock 2>/dev/null || true
Xvfb ${DISPLAY_NUM} -screen 0 ${RESOLUTION} -ac +extension GLX +render -noreset &
XVFB_PID=$!
echo "[STARTUP] Xvfb PID: ${XVFB_PID}"

# Wait for Xvfb to be ready
for i in $(seq 1 20); do
    if [ -e /tmp/.X11-unix/X${DISPLAY_NUM#:} ]; then
        echo "[STARTUP] Xvfb ready after ${i}s"
        break
    fi
    sleep 0.5
done
export DISPLAY=${DISPLAY_NUM}

# ── 2. Start x11vnc (VNC server) ─────────────────────────────────────────────
echo "[STARTUP] Starting x11vnc on port ${VNC_PORT}"
if [ -f /root/.vnc/passwd ]; then
    x11vnc -display ${DISPLAY_NUM} \
           -rfbauth /root/.vnc/passwd \
           -rfbport ${VNC_PORT} \
           -forever -shared -noxdamage \
           -bg -o /workspace/logs/x11vnc.log
else
    # No password (development mode)
    x11vnc -display ${DISPLAY_NUM} \
           -nopw -rfbport ${VNC_PORT} \
           -forever -shared -noxdamage \
           -bg -o /workspace/logs/x11vnc.log
fi
sleep 1

# ── 3. Start noVNC (WebSocket proxy → browser access) ─────────────────────────
echo "[STARTUP] Starting noVNC on port ${NOVNC_PORT}"
NOVNC_DIR=""
for d in /usr/share/novnc /usr/local/share/novnc /opt/novnc; do
    if [ -d "$d" ]; then
        NOVNC_DIR="$d"
        break
    fi
done

if [ -n "$NOVNC_DIR" ]; then
    websockify --daemon \
               --web "${NOVNC_DIR}" \
               ${NOVNC_PORT} \
               localhost:${VNC_PORT} \
               >> /workspace/logs/websockify.log 2>&1
    sleep 1
    echo "[STARTUP] noVNC web UI  → http://localhost:${NOVNC_PORT}/vnc.html"
    echo "[STARTUP] VNC raw       → vnc://localhost:${VNC_PORT}"
    echo "[STARTUP] VNC password  → qmlplace"
else
    echo "[WARNING] noVNC directory not found. Browser access unavailable."
    echo "[STARTUP] VNC raw       → vnc://localhost:${VNC_PORT}"
fi

echo ""
echo "[STARTUP] ─────────────────────────────────────────────────"
echo "[STARTUP]  Open in browser: http://localhost:${NOVNC_PORT}/vnc.html"
echo "[STARTUP] ─────────────────────────────────────────────────"
echo ""

# ── 4. Launch QML·PLACE ───────────────────────────────────────────────────────
echo "[STARTUP] Launching QML·PLACE PyQt6 application..."
cd /workspace

# Trap to clean up background processes on exit
cleanup() {
    echo "[SHUTDOWN] Stopping background services..."
    kill ${XVFB_PID} 2>/dev/null || true
    pkill x11vnc 2>/dev/null || true
    pkill websockify 2>/dev/null || true
}
trap cleanup EXIT SIGTERM SIGINT

exec python main.py
