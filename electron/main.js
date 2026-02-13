const { app, BrowserWindow, Tray, Menu, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

// Handle Squirrel startup events on Windows
if (require('electron-squirrel-startup')) {
  app.quit();
}

let mainWindow = null;
let tray = null;
let pythonProcess = null;
let serverReady = false;
const PYTHON_PORT = 7860;

// Determine if we're in development or production
const isDev = !app.isPackaged;

// Get paths
const getAppPath = () => {
  if (isDev) {
    // In development, use the parent directory
    return path.join(__dirname, '..');
  } else {
    // In production, use extraResources/app
    return path.join(process.resourcesPath, 'app');
  }
};

const getPythonPath = () => {
  const appPath = getAppPath();

  if (isDev) {
    // In development, use system Python
    return process.platform === 'win32' ? 'python' : 'python3';
  } else {
    // In production, use bundled Python
    if (process.platform === 'win32') {
      return path.join(appPath, 'python', 'python.exe');
    } else if (process.platform === 'darwin') {
      return path.join(appPath, 'python', 'bin', 'python3');
    } else {
      return path.join(appPath, 'python', 'bin', 'python3');
    }
  }
};

// Start Python server
function startPythonServer() {
  return new Promise((resolve, reject) => {
    const appPath = getAppPath();
    const pythonPath = getPythonPath();
    const scriptPath = path.join(appPath, 'run_webui_dash.py');

    console.log('Starting Python server...');
    console.log('App path:', appPath);
    console.log('Python path:', pythonPath);
    console.log('Script path:', scriptPath);

    // Check if script exists
    if (!fs.existsSync(scriptPath)) {
      reject(new Error(`Script not found: ${scriptPath}`));
      return;
    }

    // Spawn Python process
    pythonProcess = spawn(pythonPath, [scriptPath, '--port', PYTHON_PORT.toString()], {
      cwd: appPath,
      env: { ...process.env, PYTHONUNBUFFERED: '1' }
    });

    pythonProcess.stdout.on('data', (data) => {
      const output = data.toString();
      console.log(`[Python]: ${output}`);

      // Check if server is ready
      if (output.includes('Dash is running on') || output.includes('Running on')) {
        if (!serverReady) {
          serverReady = true;
          console.log('Python server is ready!');
          resolve();
        }
      }
    });

    pythonProcess.stderr.on('data', (data) => {
      console.error(`[Python Error]: ${data.toString()}`);
    });

    pythonProcess.on('error', (error) => {
      console.error('Failed to start Python server:', error);
      reject(error);
    });

    pythonProcess.on('close', (code) => {
      console.log(`Python server exited with code ${code}`);
      if (!serverReady && code !== 0) {
        reject(new Error(`Python server failed to start (exit code ${code})`));
      }
    });

    // Timeout after 30 seconds
    setTimeout(() => {
      if (!serverReady) {
        reject(new Error('Python server startup timeout'));
      }
    }, 30000);
  });
}

// Stop Python server
function stopPythonServer() {
  if (pythonProcess) {
    console.log('Stopping Python server...');
    pythonProcess.kill();
    pythonProcess = null;
  }
}

// Create main window
function createWindow() {
  // Check if icon exists
  const iconPath = path.join(__dirname, 'assets', 'icon.png');
  const hasIcon = fs.existsSync(iconPath);

  const windowOptions = {
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    title: 'TradingCrew',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: true
    },
    show: false // Don't show until ready
  };

  // Only set icon if it exists
  if (hasIcon) {
    windowOptions.icon = iconPath;
  }

  mainWindow = new BrowserWindow(windowOptions);

  // Show loading screen
  mainWindow.loadFile(path.join(__dirname, 'renderer.html'));

  // Once window is ready, start Python server
  mainWindow.once('ready-to-show', async () => {
    mainWindow.show();

    try {
      await startPythonServer();

      // Wait a bit more for server to be fully ready
      setTimeout(() => {
        mainWindow.loadURL(`http://localhost:${PYTHON_PORT}`);
      }, 2000);

    } catch (error) {
      console.error('Failed to start server:', error);
      dialog.showErrorBox(
        'Startup Error',
        `Failed to start TradingCrew server:\n\n${error.message}\n\nPlease check the logs and try again.`
      );
      app.quit();
    }
  });

  // Handle window close (minimize to tray instead)
  mainWindow.on('close', (event) => {
    if (!app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();

      // Show tray notification on first minimize (macOS and Windows)
      if (process.platform !== 'linux') {
        tray.displayBalloon({
          title: 'TradingCrew',
          content: 'App minimized to system tray. Click the icon to restore.'
        });
      }

      return false;
    }
  });

  // Open external links in default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    require('electron').shell.openExternal(url);
    return { action: 'deny' };
  });

  // Handle navigation errors
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('Failed to load:', errorCode, errorDescription);

    // Retry loading the URL a few times
    if (!serverReady && errorCode === -102) { // ERR_CONNECTION_REFUSED
      setTimeout(() => {
        mainWindow.loadURL(`http://localhost:${PYTHON_PORT}`);
      }, 1000);
    }
  });
}

// Create system tray
function createTray() {
  const iconName = process.platform === 'win32' ? 'icon.ico' :
    process.platform === 'darwin' ? 'icon.png' : // macOS tray icons should be PNG
    'icon.png';

  const iconPath = path.join(__dirname, 'assets', iconName);

  // Check if icon exists
  if (!fs.existsSync(iconPath)) {
    console.warn(`Tray icon not found: ${iconPath}`);
    console.warn('Skipping tray creation. See electron/assets/ICONS_README.md');
    return;
  }

  tray = new Tray(iconPath);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show TradingCrew',
      click: () => {
        mainWindow.show();
        if (process.platform === 'darwin') {
          app.dock.show();
        }
      }
    },
    {
      label: 'Hide TradingCrew',
      click: () => {
        mainWindow.hide();
        if (process.platform === 'darwin') {
          app.dock.hide();
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        app.isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setToolTip('TradingCrew - AI Trading Analysis');
  tray.setContextMenu(contextMenu);

  // Double-click to show window
  tray.on('double-click', () => {
    if (mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow.show();
    }
  });
}

// App ready
app.whenReady().then(() => {
  createWindow();
  createTray();

  // macOS: recreate window when dock icon clicked
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    } else {
      mainWindow.show();
    }
  });
});

// Quit when all windows closed (except macOS)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// App quitting - clean up
app.on('before-quit', () => {
  app.isQuitting = true;
  stopPythonServer();
});

app.on('will-quit', () => {
  stopPythonServer();
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
  dialog.showErrorBox('Application Error', error.message);
});
