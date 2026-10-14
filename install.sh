#!/usr/bin/env bash
# calendar-core/install.sh
# ─────────────────────────────────────────────────────────────────────────────
# CHANGELOG (newest first)
# ─────────────────────────────────────────────────────────────────────────────
#   2026-04-30  Initial standalone installer
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_BIN="$_ROOT/cli/bin"
_USER_BIN="${HOME}/bin"
_RC="${HOME}/.bashrc"
_DATA_DIR="${HOME}/.local/share/sconl"

printf '\n  calendar-core install\n  ─────────────────────\n\n'

command -v python3 &>/dev/null || { printf '  x  python3 required\n'; exit 1; }

mkdir -p "$_USER_BIN" "$_DATA_DIR"
chmod +x "$_BIN"/*

if ! grep -qF "$_BIN" "$_RC" 2>/dev/null; then
    printf '\n# calendar-core\nexport PATH="$PATH:%s"\n' "$_BIN" >> "$_RC"
    printf '  +  Added cli/bin to PATH\n'
else
    printf '  ✓  Already in PATH\n'
fi

for f in "$_BIN"/*; do
    ln -sf "$f" "$_USER_BIN/$(basename "$f")"
    printf '  ~  Linked: %s\n' "$(basename "$f")"
done

[[ ! -f "$_DATA_DIR/calendar.json" ]] && \
    cp "$_ROOT/data/calendar.json" "$_DATA_DIR/" 2>/dev/null && \
    printf '  +  Default calendar.json installed\n'

_OUT="$(python3 "$_ROOT/core/sconl_calendar/equicycle.py" --format short 2>/dev/null || true)"
[[ -n "$_OUT" ]] && \
    printf '  ✓  equicycle: %s\n' "$_OUT" || \
    printf '  !  equicycle self-test failed — check python3\n'

printf '\n  Done.\n  Run: source ~/.bashrc\n  Then: equicycle --format short\n\n'
