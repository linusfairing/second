#!/usr/bin/env bash
set -e

ROOT="/workspaces/second"
BACKEND_PORT=8000
EXPO_PORT=8081
NGROK_API="http://127.0.0.1:4040/api/tunnels"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[start]${NC} $1"; }
warn() { echo -e "${YELLOW}[start]${NC} $1"; }

cleanup() {
    echo ""
    log "Shutting down..."
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null && log "Backend stopped"
    [ -n "$EXPO_PID" ] && kill "$EXPO_PID" 2>/dev/null && log "Expo stopped"
    exit 0
}
trap cleanup SIGINT SIGTERM

# --- Kill any existing processes on our ports ---
for port in $BACKEND_PORT $EXPO_PORT; do
    pid=$(lsof -ti :"$port" 2>/dev/null || true)
    if [ -n "$pid" ]; then
        warn "Killing existing process on port $port (PID $pid)"
        kill "$pid" 2>/dev/null || true
        sleep 1
    fi
done

# Also kill any lingering ngrok
pkill -f ngrok 2>/dev/null || true

# --- Start backend ---
log "Starting backend on 0.0.0.0:$BACKEND_PORT..."
cd "$ROOT"
uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT &
BACKEND_PID=$!

# Wait for backend to be ready
for i in $(seq 1 20); do
    if curl -s -o /dev/null -w "" "http://127.0.0.1:$BACKEND_PORT/docs" 2>/dev/null; then
        log "Backend ready"
        break
    fi
    [ "$i" -eq 20 ] && { warn "Backend failed to start"; exit 1; }
    sleep 0.5
done

# --- Make port public in Codespaces ---
if [ -n "$CODESPACE_NAME" ]; then
    log "Making port $BACKEND_PORT public..."
    gh codespace ports visibility "$BACKEND_PORT:public" -c "$CODESPACE_NAME" 2>/dev/null && log "Port $BACKEND_PORT is public" || warn "Could not set port visibility (may already be public)"

    API_URL="https://${CODESPACE_NAME}-${BACKEND_PORT}.app.github.dev"
    # Update mobile .env if needed
    ENV_FILE="$ROOT/mobile/.env"
    if ! grep -q "$API_URL" "$ENV_FILE" 2>/dev/null; then
        echo "EXPO_PUBLIC_API_URL=$API_URL" > "$ENV_FILE"
        log "Updated mobile/.env with $API_URL"
    fi
fi

# --- Start Expo with tunnel ---
log "Starting Expo tunnel..."
cd "$ROOT/mobile"
npx expo start --tunnel &
EXPO_PID=$!

# Wait for tunnel to be ready
log "Waiting for tunnel..."
TUNNEL_URL=""
for i in $(seq 1 60); do
    TUNNEL_URL=$(curl -s "$NGROK_API" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'])" 2>/dev/null || true)
    if [ -n "$TUNNEL_URL" ]; then
        break
    fi
    sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
    warn "Could not get tunnel URL. Expo may still be starting — check logs above."
    wait
    exit 1
fi

# --- Generate QR code ---
EXPO_URL="exp://$(echo "$TUNNEL_URL" | sed 's|https://||')"
echo ""
echo -e "${CYAN}=== Scan this QR code with your phone camera ===${NC}"
echo ""
python3 -c "
import qrcode
qr = qrcode.QRCode(border=1, box_size=1)
qr.add_data('$EXPO_URL')
qr.make(fit=True)
qr.print_ascii(invert=True)
"
echo ""
echo -e "${CYAN}URL: $EXPO_URL${NC}"
echo -e "${CYAN}API: ${API_URL:-http://localhost:$BACKEND_PORT}${NC}"
echo ""
log "Everything is running. Press Ctrl+C to stop all services."

# Keep script alive — wait for either child to exit
wait
