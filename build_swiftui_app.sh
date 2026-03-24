#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="博文翻译助手"
BUILD_DIR="$ROOT_DIR/.build"
DIST_DIR="$ROOT_DIR/dist"
APP_DIR="$DIST_DIR/$APP_NAME.app"
MACOS_DIR="$APP_DIR/Contents/MacOS"
RESOURCES_DIR="$APP_DIR/Contents/Resources"
WORKER_DIR="$RESOURCES_DIR/PythonWorker"
EXECUTABLE="$BUILD_DIR/release/BlogTranslatorApp"
ICON_SOURCE="$ROOT_DIR/icon.png"
ICON_NAME="AppIcon"

generate_icns() {
  local source_png="$1"
  local output_icns="$2"
  local temp_dir
  local iconset_dir
  temp_dir="$(mktemp -d /tmp/blogtranslator.icon.XXXXXX)"
  iconset_dir="$temp_dir/$ICON_NAME.iconset"
  mkdir -p "$iconset_dir"

  # Build a standard macOS iconset from the chosen PNG source.
  for size in 16 32 128 256 512; do
    sips -z "$size" "$size" "$source_png" --out "$iconset_dir/icon_${size}x${size}.png" >/dev/null
    sips -z "$((size * 2))" "$((size * 2))" "$source_png" --out "$iconset_dir/icon_${size}x${size}@2x.png" >/dev/null
  done

  iconutil -c icns "$iconset_dir" -o "$output_icns"
  rm -rf "$temp_dir"
}

echo "==> Building SwiftUI app"
swift build -c release

if [[ ! -f "$EXECUTABLE" ]]; then
  echo "Missing executable: $EXECUTABLE" >&2
  exit 1
fi

echo "==> Assembling .app bundle"
rm -rf "$APP_DIR"
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR" "$WORKER_DIR"

cp "$EXECUTABLE" "$MACOS_DIR/$APP_NAME"
cp -R "$ROOT_DIR/src" "$WORKER_DIR/"

if [[ -f "$ICON_SOURCE" ]]; then
  echo "==> Generating app icon from $ICON_SOURCE"
  generate_icns "$ICON_SOURCE" "$RESOURCES_DIR/$ICON_NAME.icns"
fi

cat > "$APP_DIR/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>zh_CN</string>
  <key>CFBundleExecutable</key>
  <string>博文翻译助手</string>
  <key>CFBundleIdentifier</key>
  <string>com.duzhengtong.blogtranslator</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleIconFile</key>
  <string>AppIcon</string>
  <key>CFBundleName</key>
  <string>博文翻译助手</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0.0</string>
  <key>CFBundleVersion</key>
  <string>1.0.0</string>
  <key>LSMinimumSystemVersion</key>
  <string>14.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
PLIST

cat <<EOF
==> Done
App bundle: $APP_DIR

Current packaging notes:
- The app bundle embeds the Python worker source tree.
- It still relies on an available Python 3 runtime plus installed Python deps.
- After full Xcode installation, this script can be used for native bundle verification.
EOF
