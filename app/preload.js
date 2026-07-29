'use strict';

const { contextBridge, ipcRenderer, webUtils } = require('electron');

contextBridge.exposeInMainWorld('aesth', {
  checkEnv: () => ipcRenderer.invoke('aesth:check-env'),
  schema: () => ipcRenderer.invoke('aesth:schema'),
  probe: (file) => ipcRenderer.invoke('aesth:probe', file),
  preview: (req) => ipcRenderer.invoke('aesth:preview', req),
  snippet: (req) => ipcRenderer.invoke('aesth:snippet', req),
  pickExportPath: (suggestion) => ipcRenderer.invoke('aesth:pick-export-path', suggestion),
  exportRender: (req) => ipcRenderer.invoke('aesth:export', req),
  cancelExport: (jobId) => ipcRenderer.invoke('aesth:cancel-export', jobId),
  reveal: (file) => ipcRenderer.invoke('aesth:reveal', file),
  onProgress: (cb) => {
    const listener = (_e, msg) => cb(msg);
    ipcRenderer.on('aesth:progress', listener);
    return () => ipcRenderer.removeListener('aesth:progress', listener);
  },
  pathForFile: (file) => webUtils.getPathForFile(file),
});
