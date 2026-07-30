'use strict';

const { contextBridge, ipcRenderer, webUtils } = require('electron');

contextBridge.exposeInMainWorld('aesth', {
  checkEnv: () => ipcRenderer.invoke('aesth:check-env'),
  schema: () => ipcRenderer.invoke('aesth:schema'),
  probe: (file) => ipcRenderer.invoke('aesth:probe', file),
  pickInput: () => ipcRenderer.invoke('aesth:pick-input'),
  preview: (req) => ipcRenderer.invoke('aesth:preview', req),
  snippet: (req) => ipcRenderer.invoke('aesth:snippet', req),
  pickExportPath: (suggestion, audioOnly) => ipcRenderer.invoke('aesth:pick-export-path', suggestion, audioOnly),
  exportRender: (req) => ipcRenderer.invoke('aesth:export', req),
  cancelExport: (jobId) => ipcRenderer.invoke('aesth:cancel-export', jobId),
  reveal: (file) => ipcRenderer.invoke('aesth:reveal', file),
  thumbs: () => ipcRenderer.invoke('aesth:thumbs'),
  cacheInfo: () => ipcRenderer.invoke('aesth:cache-info'),
  cacheClear: () => ipcRenderer.invoke('aesth:cache-clear'),
  cacheReveal: () => ipcRenderer.invoke('aesth:cache-reveal'),
  onProgress: (cb) => {
    const listener = (_e, msg) => cb(msg);
    ipcRenderer.on('aesth:progress', listener);
    return () => ipcRenderer.removeListener('aesth:progress', listener);
  },
  pathForFile: (file) => webUtils.getPathForFile(file),
});
