#!/bin/bash

# ==============================================================================
# Job Radar AI - macOS Otomatik Sabah Taraması Kurulum Scripti (launchd)
# ==============================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
PLIST_NAME="com.jobradar.daily.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$LAUNCH_AGENTS_DIR/$PLIST_NAME"
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python"

# 1. Sanal ortam kontrolü
if [ ! -f "$PYTHON_PATH" ]; then
    echo "❌ Sanal ortam bulunamadı ($PYTHON_PATH). Lütfen önce venv kurulumunu yapın."
    exit 1
fi

# 2. LaunchAgents klasörünü oluştur
mkdir -p "$LAUNCH_AGENTS_DIR"
mkdir -p "$SCRIPT_DIR/data"

# 3. Eğer eski servis varsa durdur ve kaldır
if launchctl list | grep -q "com.jobradar.daily"; then
    echo "🔄 Eski zamanlanmış görev kaldırılıyor..."
    launchctl unload "$TARGET_PLIST" 2>/dev/null || true
fi

# 4. plist dosyasını oluştur (Her sabah 09:00'da çalışır)
cat <<EOF > "$TARGET_PLIST"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jobradar.daily</string>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>$SCRIPT_DIR</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH</string>
    </dict>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$SCRIPT_DIR/main.py</string>
        <string>--run-once</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/data/scheduler_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/data/scheduler_stderr.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

# 5. Servisi başlat
launchctl load "$TARGET_PLIST"

echo ""
echo "================================================================="
echo "✅ Job Radar AI Sabah Taraması Başarıyla Kuruldu!"
echo "⏰ Çalışma Zamanı: Her sabah saat 09:00"
echo "📂 Proje Dizini: $SCRIPT_DIR"
echo "📄 Görev Dosyası: $TARGET_PLIST"
echo "📋 Log Dosyası: $SCRIPT_DIR/data/scheduler_stdout.log"
echo "================================================================="
echo "💡 İptal etmek isterseniz: bash scripts/uninstall_mac_scheduler.sh"
echo ""
