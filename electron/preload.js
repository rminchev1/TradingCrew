/**
 * Preload script - runs before renderer process loads
 * Provides secure bridge between main and renderer processes
 */

const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electron', {
  // Add any IPC methods here if needed in the future
  platform: process.platform,
  version: process.versions.electron
});

console.log('Preload script loaded');
