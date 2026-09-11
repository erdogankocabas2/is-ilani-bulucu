#!/bin/bash

# ==============================================================================
# Job Radar AI - macOS Zamanlayıcı Kaldırma Scripti
# ==============================================================================

PLIST_NAME="com.jobradar.daily.plist"
TARGET_PLIST="$HOME/Library/LaunchAgents/$PLIST_NAME"

if [ -f "$TARGET_PLIST" ]; then
    launchctl unload "$TARGET_PLIST" 2>/dev/null || true
    rm -f "$TARGET_PLIST"
    echo "✅ Sabah zamanlayıcısı başarıyla kaldırıldı."
else
    echo "ℹ️ Kurulu bir zamanlayıcı bulunamadı."
fi
