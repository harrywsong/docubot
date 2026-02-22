import { useState, useEffect } from 'react';
import { FolderPlus, X, Folder, ChevronDown, ChevronUp, File } from 'lucide-react';
import { addFolder, removeFolder, listFolders, listFolderFiles } from '../api';

export default function FolderManagement({ onToast }) {
  const [folders, setFolders] = useState([]);
  const [folderPath, setFolderPath] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandedFolders, setExpandedFolders] = useState({});
  const [folderFiles, setFolderFiles] = useState({});
  const [loadingFiles, setLoadingFiles] = useState({});

  useEffect(() => {
    loadFolders();
  }, []);

  async function loadFolders() {
    try {
      const response = await listFolders();
      setFolders(response.folders);
    } catch (error) {
      onToast(`Failed to load folders: ${error.message}`, 'error');
    }
  }

  async function toggleFolder(folderId, folderPath) {
    const isExpanded = expandedFolders[folderId];
    
    if (!isExpanded) {
      // Load files for this folder
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
      await addFolder(folderPath);
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
      await removeFolder(path);
      onToast('Folder removed successfully', 'success');
      await loadFolders();
    } catch (error) {
      onToast(`Failed to remove folder: ${error.message}`, 'error');
    }
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
        <Folder className="w-4 h-4" />
        Watched Folders
      </h3>
      
      <form onSubmit={handleAddFolder} className="space-y-3">
        <input
          type="text"
          className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg
                     text-sm text-gray-200 placeholder-gray-500
                     focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50
                     transition-all duration-200
                     disabled:opacity-50 disabled:cursor-not-allowed"
          placeholder="Enter folder path..."
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
            <div key={folder.id} className="glass-card rounded-lg overflow-hidden">
              <div className="px-3 py-2 flex items-center justify-between gap-2 group hover:border-white/20 transition-all duration-200">
                <button
                  onClick={() => toggleFolder(folder.id, folder.path)}
                  className="flex-1 flex items-center gap-2 text-left"
                >
                  {expandedFolders[folder.id] ? (
                    <ChevronUp className="w-4 h-4 text-gray-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-gray-400" />
                  )}
                  <span className="text-sm text-gray-300 truncate">
                    {folder.path}
                  </span>
                </button>
                <button
                  className="p-1 rounded-md text-gray-400 hover:text-red-400 hover:bg-red-500/10
                             transition-all duration-200 opacity-0 group-hover:opacity-100"
                  onClick={() => handleRemoveFolder(folder.path)}
                  title="Remove folder"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              
              {expandedFolders[folder.id] && (
                <div className="px-3 py-2 border-t border-white/10 bg-white/[0.02]">
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
                        <li key={idx} className="flex items-center gap-2 text-xs text-gray-400 py-1">
                          <File className="w-3 h-3 flex-shrink-0" />
                          <span className="truncate" title={file}>{file}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-gray-500 text-center py-2">
                      No files found in this folder
                    </p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-500 text-center py-4">
          No folders added yet. Add a folder to get started.
        </p>
      )}
    </div>
  );
}
