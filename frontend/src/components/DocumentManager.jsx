import { useState, useEffect, useRef } from 'react';
import { FolderPlus, X, Folder, ChevronDown, ChevronUp, File, Play, Trash2, FileCheck, FileX, FileWarning, Loader2, Upload } from 'lucide-react';
import { addFolder, removeFolder, listFolders, listFolderFiles, startProcessing, connectProcessingStream, clearUserData, syncToPi } from '../api';

export default function DocumentManager({ userId, onToast }) {
  const [folders, setFolders] = useState([]);
  const [folderPath, setFolderPath] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandedFolders, setExpandedFolders] = useState({});
  const [folderFiles, setFolderFiles] = useState({});
  const [loadingFiles, setLoadingFiles] = useState({});
  const [processing, setProcessing] = useState(false);
  const [status, setStatus] = useState({
    processed: 0,
    skipped: 0,
    failed: 0,
    failed_files: [],
    processed_files: [],
    skipped_files: []
  });
  const [showProcessed, setShowProcessed] = useState(false);
  const [showSkipped, setShowSkipped] = useState(false);
  const [showFailed, setShowFailed] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    loadFolders();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [userId]);

  async function loadFolders() {
    try {
      const response = await listFolders(userId);
      setFolders(response.folders);
    } catch (error) {
      onToast(`Failed to load folders: ${error.message}`, 'error');
    }
  }

  async function toggleFolder(folderId, folderPath) {
    const isExpanded = expandedFolders[folderId];
    
    if (!isExpanded) {
      setLoadingFiles(prev => ({ ...prev, [folderId]: true }));
      try {
        const response = await listFolderFiles(folderPath);
        setFolderFiles(prev => ({ ...prev, [folderId]: response.files || [] }));
        setExpandedFolders(prev => ({ ...prev, [folderId]: true }));
      } catch (error) {
        onToast(`Failed to load files: ${error.message}`, 'error');
      } finally {
        setLoadingFiles(prev => ({ ...prev, [folderId]: false }));
      }
    } else {
      setExpandedFolders(prev => ({ ...prev, [folderId]: false }));
    }
  }

  async function handleAddFolder(e) {
    e.preventDefault();
    if (!folderPath.trim()) return;

    setLoading(true);
    try {
      await addFolder(folderPath, userId);
      onToast('Folder added successfully', 'success');
      setFolderPath('');
      await loadFolders();
    } catch (error) {
      onToast(error.message, 'error');
    } finally {
      setLoading(false);
    }
  }

  async function handleRemoveFolder(path) {
    try {
      await removeFolder(path, userId);
      onToast('Folder removed successfully', 'success');
      await loadFolders();
    } catch (error) {
      onToast(`Failed to remove folder: ${error.message}`, 'error');
    }
  }

  async function handleStartProcessing() {
    try {
      await startProcessing();
      setProcessing(true);
      setStatus({ 
        processed: 0, 
        skipped: 0, 
        failed: 0, 
        failed_files: [],
        processed_files: [],
        skipped_files: []
      });
      
      wsRef.current = connectProcessingStream(
        (data) => {
          if (data.type === 'status') {
            setStatus(prev => ({
              ...prev,
              processed: data.processed,
              skipped: data.skipped,
              failed: data.failed,
              processed_files: data.processed_files || prev.processed_files,
              skipped_files: data.skipped_files || prev.skipped_files,
              failed_files: data.failed_files || prev.failed_files
            }));
            setProcessing(data.is_processing);
          } else if (data.type === 'complete') {
            setStatus({
              processed: data.processed,
              skipped: data.skipped,
              failed: data.failed,
              failed_files: data.failed_files || [],
              processed_files: data.processed_files || [],
              skipped_files: data.skipped_files || []
            });
            setProcessing(false);
            onToast('Processing complete', 'success');
            
            if (wsRef.current) {
              wsRef.current.close();
              wsRef.current = null;
            }
          } else if (data.type === 'error') {
            onToast(`Processing error: ${data.message}`, 'error');
            setProcessing(false);
            
            if (wsRef.current) {
              wsRef.current.close();
              wsRef.current = null;
            }
          }
        },
        (error) => {
          onToast('WebSocket connection error', 'error');
          setProcessing(false);
        }
      );
    } catch (error) {
      onToast(error.message, 'error');
      setProcessing(false);
    }
  }

  async function handleClearData() {
    if (!confirm('Are you sure you want to clear all YOUR data? This will delete all your processed documents and reset your processing state.')) {
      return;
    }
    
    try {
      const result = await clearUserData(userId);
      setStatus({ 
        processed: 0, 
        skipped: 0, 
        failed: 0, 
        failed_files: [],
        processed_files: [],
        skipped_files: []
      });
      onToast(result.message, 'success');
    } catch (error) {
      onToast(`Failed to clear data: ${error.message}`, 'error');
    }
  }

  async function handleSyncToPi() {
    if (!confirm('Sync all processed data to Raspberry Pi? This will copy the vector store and database to your Pi.')) {
      return;
    }
    
    setSyncing(true);
    try {
      const result = await syncToPi();
      onToast(result.message, 'success');
    } catch (error) {
      onToast(`Failed to sync: ${error.message}`, 'error');
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Folder Management Section */}
      <div className="glass-card p-6 rounded-xl">
        <h3 className="text-lg font-semibold text-foreground flex items-center gap-2 mb-4">
          <Folder className="w-5 h-5" />
          Your Folders
        </h3>
        
        <form onSubmit={handleAddFolder} className="space-y-3 mb-6">
          <input
            type="text"
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg
                       text-sm text-foreground placeholder-foreground-muted
                       focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent/50
                       transition-all duration-200
                       disabled:opacity-50 disabled:cursor-not-allowed"
            placeholder="Enter folder path (e.g., C:\Users\harry\Documents)..."
            value={folderPath}
            onChange={(e) => setFolderPath(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            className="btn-primary w-full flex items-center justify-center gap-2"
            disabled={loading || !folderPath.trim()}
          >
            <FolderPlus className="w-4 h-4" />
            {loading ? 'Adding...' : 'Add Folder'}
          </button>
        </form>

        {folders.length > 0 ? (
          <div className="space-y-2">
            {folders.map((folder) => (
              <div key={folder.id} className="bg-white/[0.03] border border-white/10 rounded-lg overflow-hidden hover:border-white/20 transition-all duration-200">
                <div className="px-4 py-3 flex items-center justify-between gap-2 group">
                  <button
                    onClick={() => toggleFolder(folder.id, folder.path)}
                    className="flex-1 flex items-center gap-2 text-left"
                  >
                    {expandedFolders[folder.id] ? (
                      <ChevronUp className="w-4 h-4 text-foreground-muted" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-foreground-muted" />
                    )}
                    <span className="text-sm text-foreground truncate">
                      {folder.path}
                    </span>
                  </button>
                  <button
                    className="p-1.5 rounded-md text-foreground-muted hover:text-red-400 hover:bg-red-500/10
                               transition-all duration-200 opacity-0 group-hover:opacity-100"
                    onClick={() => handleRemoveFolder(folder.path)}
                    title="Remove folder"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                
                {expandedFolders[folder.id] && (
                  <div className="px-4 py-3 border-t border-white/10 bg-white/[0.02]">
                    {loadingFiles[folder.id] ? (
                      <div className="flex items-center justify-center py-4">
                        <div className="flex gap-1">
                          <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
                          <div className="w-2 h-2 rounded-full bg-accent animate-pulse animation-delay-100" />
                          <div className="w-2 h-2 rounded-full bg-accent animate-pulse animation-delay-200" />
                        </div>
                      </div>
                    ) : folderFiles[folder.id] && folderFiles[folder.id].length > 0 ? (
                      <ul className="space-y-1 max-h-60 overflow-y-auto custom-scrollbar">
                        {folderFiles[folder.id].map((file, idx) => (
                          <li key={idx} className="flex items-center gap-2 text-xs text-foreground-muted py-1">
                            <File className="w-3 h-3 flex-shrink-0" />
                            <span className="truncate" title={file}>{file}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-foreground-muted text-center py-2">
                        No supported files found in this folder
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-foreground-muted text-center py-8 bg-white/[0.02] rounded-lg border border-white/10">
            No folders added yet. Add a folder to get started.
          </p>
        )}
      </div>

      {/* Processing Section */}
      <div className="glass-card p-6 rounded-xl">
        <h3 className="text-lg font-semibold text-foreground flex items-center gap-2 mb-4">
          <FileCheck className="w-5 h-5" />
          Process Documents
        </h3>
        
        <div className="space-y-3">
          <button
            className="btn-primary w-full flex items-center justify-center gap-2"
            onClick={handleStartProcessing}
            disabled={processing || folders.length === 0}
          >
            {processing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Process All Folders
              </>
            )}
          </button>

          <button
            className="btn-secondary w-full flex items-center justify-center gap-2
                       hover:bg-blue-500/10 hover:border-blue-500/30 hover:text-blue-400
                       transition-all duration-200"
            onClick={handleSyncToPi}
            disabled={processing || syncing}
          >
            {syncing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Syncing...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                Sync to Raspberry Pi
              </>
            )}
          </button>

          <button
            className="btn-secondary w-full flex items-center justify-center gap-2
                       hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-400
                       transition-all duration-200"
            onClick={handleClearData}
            disabled={processing}
          >
            <Trash2 className="w-4 h-4" />
            Clear My Data
          </button>
        </div>

        {(processing || status.processed > 0 || status.skipped > 0 || status.failed > 0) && (
          <div className="mt-6 p-4 bg-white/[0.03] border border-white/10 rounded-lg space-y-4">
            <div className="grid grid-cols-3 gap-4">
              {/* Processed */}
              <div className="flex flex-col items-center">
                <div className="flex items-center justify-center gap-1 text-emerald-400 mb-1">
                  <FileCheck className="w-4 h-4" />
                </div>
                <div className="text-2xl font-bold text-emerald-400">{status.processed}</div>
                <div className="text-xs text-foreground-muted mb-2">Processed</div>
                {status.processed > 0 && (
                  <button
                    onClick={() => setShowProcessed(!showProcessed)}
                    className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1 transition-colors"
                  >
                    {showProcessed ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    {showProcessed ? 'Hide' : 'Show'}
                  </button>
                )}
              </div>
              
              {/* Skipped */}
              <div className="flex flex-col items-center">
                <div className="flex items-center justify-center gap-1 text-amber-400 mb-1">
                  <FileWarning className="w-4 h-4" />
                </div>
                <div className="text-2xl font-bold text-amber-400">{status.skipped}</div>
                <div className="text-xs text-foreground-muted mb-2">Skipped</div>
                {status.skipped > 0 && (
                  <button
                    onClick={() => setShowSkipped(!showSkipped)}
                    className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1 transition-colors"
                  >
                    {showSkipped ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    {showSkipped ? 'Hide' : 'Show'}
                  </button>
                )}
              </div>
              
              {/* Failed */}
              <div className="flex flex-col items-center">
                <div className="flex items-center justify-center gap-1 text-red-400 mb-1">
                  <FileX className="w-4 h-4" />
                </div>
                <div className="text-2xl font-bold text-red-400">{status.failed}</div>
                <div className="text-xs text-foreground-muted mb-2">Failed</div>
                {status.failed > 0 && (
                  <button
                    onClick={() => setShowFailed(!showFailed)}
                    className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1 transition-colors"
                  >
                    {showFailed ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    {showFailed ? 'Hide' : 'Show'}
                  </button>
                )}
              </div>
            </div>
            
            {/* File Lists */}
            {showProcessed && status.processed_files && status.processed_files.length > 0 && (
              <div className="pt-3 border-t border-white/10">
                <div className="text-xs font-semibold text-emerald-400 mb-2">Processed Files:</div>
                <ul className="space-y-1 max-h-40 overflow-y-auto custom-scrollbar">
                  {status.processed_files.map((file, idx) => (
                    <li key={idx} className="text-xs text-foreground-muted pl-4 truncate" title={file}>
                      • {file}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {showSkipped && status.skipped_files && status.skipped_files.length > 0 && (
              <div className="pt-3 border-t border-white/10">
                <div className="text-xs font-semibold text-amber-400 mb-2">Skipped Files:</div>
                <ul className="space-y-1 max-h-40 overflow-y-auto custom-scrollbar">
                  {status.skipped_files.map((file, idx) => (
                    <li key={idx} className="text-xs text-foreground-muted pl-4 truncate" title={file}>
                      • {file}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {showFailed && status.failed_files && status.failed_files.length > 0 && (
              <div className="pt-3 border-t border-white/10">
                <div className="text-xs font-semibold text-red-400 mb-2">Failed Files:</div>
                <ul className="space-y-2 max-h-40 overflow-y-auto custom-scrollbar">
                  {status.failed_files.map((item, idx) => (
                    <li key={idx} className="text-xs text-foreground-muted pl-4">
                      <div className="text-foreground truncate" title={item.file}>• {item.file}</div>
                      <div className="text-red-400 pl-2 mt-1">{item.error}</div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
