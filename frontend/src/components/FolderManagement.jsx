import { useState, useEffect } from 'react';
import { addFolder, removeFolder, listFolders } from '../api';

export default function FolderManagement({ onToast }) {
  const [folders, setFolders] = useState([]);
  const [folderPath, setFolderPath] = useState('');
  const [loading, setLoading] = useState(false);

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
    <div className="folder-section">
      <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>
        Watched Folders
      </h3>
      
      <form onSubmit={handleAddFolder} className="folder-input-group">
        <input
          type="text"
          className="folder-input"
          placeholder="Enter folder path..."
          value={folderPath}
          onChange={(e) => setFolderPath(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="add-folder-btn"
          disabled={loading || !folderPath.trim()}
        >
          {loading ? 'Adding...' : 'Add Folder'}
        </button>
      </form>

      {folders.length > 0 ? (
        <div className="folder-list">
          {folders.map((folder) => (
            <div key={folder.id} className="folder-tag">
              <span>{folder.path}</span>
              <button
                className="remove-folder-btn"
                onClick={() => handleRemoveFolder(folder.path)}
                title="Remove folder"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      ) : (
        <p style={{ fontSize: '13px', color: '#666' }}>
          No folders added yet. Add a folder to get started.
        </p>
      )}
    </div>
  );
}
