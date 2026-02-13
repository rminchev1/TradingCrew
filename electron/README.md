# TradingCrew Desktop Application

Electron wrapper for TradingCrew that provides a native desktop experience on macOS, Windows, and Linux.

## Features

- **Native Desktop App**: Runs as a standalone application with system tray support
- **Cross-Platform**: Single codebase for macOS, Windows, and Linux
- **System Tray Integration**: Minimize to tray, quick access from taskbar
- **Auto-Start Server**: Python backend starts automatically on app launch
- **Offline Capable**: No internet required for local operation (except API calls)
- **Native Look & Feel**: Uses system-native window chrome and controls

## Prerequisites

### For Development/Building

1. **Node.js 18+** - [Download](https://nodejs.org/)
2. **Python 3.11+** - Must be installed and in PATH
3. **Git** - For version control

### Platform-Specific Requirements

#### macOS
- macOS 10.15+ (Catalina or newer)
- Xcode Command Line Tools (for building): `xcode-select --install`

#### Windows
- Windows 10/11
- Windows Build Tools (optional, for native modules): `npm install -g windows-build-tools`

#### Linux
- Ubuntu 18.04+ / Fedora 32+ / Debian 10+
- Required packages:
  ```bash
  sudo apt-get install -y libgtk-3-0 libnotify4 libnss3 libxss1 libxtst6 xdg-utils libatspi2.0-0 libdrm2 libgbm1 libxcb-dri3-0
  ```

## Quick Start

### 1. Install Dependencies

```bash
cd electron
npm install
```

### 2. Run in Development Mode

```bash
npm start
```

This will:
- Start the Electron app
- Auto-launch the Python Dash server
- Open the app window when ready

### 3. Build for Distribution

#### macOS
```bash
./build.sh
# Or manually:
npm run build:mac
```

Output: `../dist/TradingCrew-0.3.0.dmg` and `.zip`

#### Windows
```cmd
build.bat
REM Or manually:
npm run build:win
```

Output: `../dist/TradingCrew Setup 0.3.0.exe` and portable `.exe`

#### Linux
```bash
./build.sh
# Or manually:
npm run build:linux
```

Output: `../dist/TradingCrew-0.3.0.AppImage`, `.deb`, and `.rpm`

#### All Platforms (on macOS/Linux)
```bash
npm run build:all
```

## Project Structure

```
electron/
├── main.js              # Main process (app lifecycle, Python server)
├── preload.js           # Security bridge between main/renderer
├── renderer.html        # Loading screen UI
├── renderer.css         # Loading screen styles
├── package.json         # Electron config and build settings
├── entitlements.mac.plist  # macOS security permissions
├── build.sh             # Build script for macOS/Linux
├── build.bat            # Build script for Windows
├── assets/
│   ├── icon.icns        # macOS icon (1024x1024)
│   ├── icon.ico         # Windows icon (multi-size)
│   ├── icon.png         # Linux icon (512x512)
│   └── ICONS_README.md  # Icon creation guide
└── README.md            # This file
```

## How It Works

### Architecture

```
Electron App (main.js)
    ├─> Spawns Python process (run_webui_dash.py)
    ├─> Creates BrowserWindow
    ├─> Loads http://localhost:7860
    └─> Creates System Tray icon

Python Server (Dash/Flask)
    └─> Serves WebUI on port 7860
```

### Startup Flow

1. **Electron launches** → Shows loading screen
2. **Spawns Python subprocess** → `python3 run_webui_dash.py --port 7860`
3. **Waits for server ready** → Monitors stdout for "Dash is running on"
4. **Loads app** → BrowserWindow navigates to `http://localhost:7860`
5. **Creates tray icon** → App can minimize to system tray

### Shutdown Flow

1. **User clicks Quit** → `app.quit()` triggered
2. **Before quit hook** → Kills Python subprocess
3. **Clean exit** → All processes terminated

## Development

### Testing Without Building

```bash
npm start
```

This runs in development mode where:
- Uses system Python (not bundled)
- Fast reload (no build step)
- Console logs visible

### Building Test Package (Faster)

```bash
npm run pack
```

Creates unpacked app in `dist/` without creating installer. Good for quick testing.

### Full Build Process

```bash
npm run build
```

Creates:
- Installers (DMG, NSIS, AppImage)
- Portable executables
- Auto-update artifacts (if configured)

## Configuration

### Changing Port

Edit `electron/main.js`:

```javascript
const PYTHON_PORT = 7860;  // Change to your preferred port
```

Also update `run_webui_dash.py` if needed.

### App Metadata

Edit `electron/package.json`:

```json
{
  "name": "tradingcrew-desktop",
  "version": "0.3.0",
  "description": "...",
  "author": "...",
  "build": {
    "appId": "com.tradingcrew.desktop",
    "productName": "TradingCrew"
  }
}
```

### Icon Customization

See `assets/ICONS_README.md` for detailed instructions on creating app icons.

Quick summary:
1. Create 1024x1024px PNG logo
2. Convert to platform-specific formats:
   - macOS: `.icns` (use `png2icns`)
   - Windows: `.ico` (use ImageMagick or online tool)
   - Linux: `.png` (use original or 512x512 version)

## System Tray

The app minimizes to the system tray instead of fully quitting when you close the window.

**Controls:**
- **Single click** (Windows/Linux): Open context menu
- **Double click**: Show/hide window
- **Right click**: Show context menu

**Menu Options:**
- Show TradingCrew
- Hide TradingCrew
- Quit

To fully quit, use the tray menu or `Cmd+Q` (macOS) / `Alt+F4` (Windows).

## Troubleshooting

### Python Server Won't Start

**Symptoms:** Loading screen stuck on "Starting analysis engine..."

**Solutions:**
1. Check Python is in PATH: `python3 --version`
2. Check dependencies installed: `pip install -r requirements.txt`
3. Test server manually: `python3 run_webui_dash.py`
4. Check console logs in Electron for errors

### App Won't Launch

**macOS:**
- If "damaged" error: `xattr -cr /Applications/TradingCrew.app`
- If unsigned warning: Right-click → Open → Open anyway

**Windows:**
- If SmartScreen blocks: Click "More info" → "Run anyway"
- Antivirus may quarantine: Add exception

**Linux:**
- Make AppImage executable: `chmod +x TradingCrew-0.3.0.AppImage`
- Check dependencies: See Prerequisites above

### Build Fails

**Common issues:**
1. **Missing icons**: Non-critical, app will build without them
2. **Node modules**: Delete `node_modules`, run `npm install` again
3. **Python bundling**: Ensure Python 3.11+ is in PATH
4. **Disk space**: Builds can be large (500MB - 2GB)

### Port Already in Use

If port 7860 is taken:
1. Change `PYTHON_PORT` in `main.js`
2. Update Python server to match

Or kill the process using the port:
```bash
# macOS/Linux
lsof -ti:7860 | xargs kill -9

# Windows
netstat -ano | findstr :7860
taskkill /PID <pid> /F
```

## Advanced Configuration

### Auto-Updates

To enable auto-updates, configure a release server in `package.json`:

```json
{
  "build": {
    "publish": {
      "provider": "github",
      "owner": "your-org",
      "repo": "tradingcrew"
    }
  }
}
```

Then implement update checks in `main.js` using `electron-updater`.

### Custom Splash Screen

Edit `renderer.html` and `renderer.css` to customize the loading screen.

### Menu Bar Customization

Add custom menu items in `main.js`:

```javascript
const { Menu } = require('electron');

const menu = Menu.buildFromTemplate([
  {
    label: 'File',
    submenu: [
      { role: 'quit' }
    ]
  },
  // ... more menu items
]);

Menu.setApplicationMenu(menu);
```

### Deep Links

To handle custom URL schemes (e.g., `tradingcrew://`), add to `package.json`:

```json
{
  "build": {
    "protocols": {
      "name": "tradingcrew",
      "schemes": ["tradingcrew"]
    }
  }
}
```

## Security

### Content Security

- **Node Integration**: Disabled in renderer
- **Context Isolation**: Enabled (recommended)
- **Preload Script**: Whitelisted APIs only
- **Web Security**: Enabled

### Python Subprocess

- Runs with same permissions as Electron app
- Environment variables isolated
- Clean shutdown on app quit

### Network

- Python server binds to `localhost` only
- No external access by default
- HTTPS not required (local connection)

## Distribution

### File Sizes (Approximate)

- **macOS DMG**: 150-300 MB
- **Windows Installer**: 100-200 MB
- **Linux AppImage**: 150-250 MB

Sizes vary based on:
- Python dependencies bundled
- Number of packages
- Compression settings

### Code Signing

**macOS:**
```bash
export APPLE_ID="your@email.com"
export APPLE_ID_PASSWORD="app-specific-password"
npm run build:mac
```

**Windows:**
Requires code signing certificate. Configure in `package.json`:

```json
{
  "build": {
    "win": {
      "certificateFile": "path/to/cert.pfx",
      "certificatePassword": "password"
    }
  }
}
```

## Performance

- **Startup time**: 5-10 seconds (Python server init)
- **Memory usage**: 200-400 MB (Chromium + Python)
- **CPU**: Idle ~1-2%, Active 5-20% (depends on analysis)

## License

Same as parent project (see main `LICENSE` file).

## Support

For issues specific to the desktop app, please check:
1. This README
2. Console logs (`View → Toggle Developer Tools`)
3. Python server logs
4. GitHub Issues

## Resources

- [Electron Documentation](https://www.electronjs.org/docs)
- [electron-builder](https://www.electron.build/)
- [TradingCrew Main Docs](../docs/README.md)
