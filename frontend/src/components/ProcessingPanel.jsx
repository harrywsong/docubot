import { useState, useEffect, useRef } from 'react';
import { Play, Trash2, FileCheck, FileX, FileWarning, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { startProcessing, connectProcessingStream, clearAllData } from '../api';

export default function ProcessingPanel({ onToast }) {
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
  const wsRef = useRef(null);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

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
      
      // Connect to WebSocket for real-time updates
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
    if (!confirm('Are you sure you want to clear all data? This will delete all processed documents and reset the database.')) {
      return;
    }
    
    try {
      const result = await clearAllData();
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

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
        <FileCheck className="w-4 h-4" />
        Document Processing
      </h3>
      
      <div className="space-y-2">
        <button
          className="btn-primary w-full flex items-center justify-center gap-2"
          onClick={handleStartProcessing}
          disabled={processing}
        >
          {processing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Process Documents
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
          Clear All Data
        </button>
      </div>

      {(processing || status.processed > 0 || status.skipped > 0 || status.failed > 0) && (
        <div className="glass-card p-4 rounded-xl space-y-3">
          <div className="grid grid-cols-3 gap-3">
            {/* Processed */}
            <div className="flex flex-col items-center">
              <div className="flex items-center justify-center gap-1 text-emerald-400 mb-1">
                <FileCheck className="w-4 h-4" />
              </div>
              <div className="text-2xl font-bold text-emerald-400">{status.processed}</div>
              <div className="text-xs text-gray-500 mb-2">Processed</div>
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
              <div className="text-xs text-gray-500 mb-2">Skipped</div>
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
              <div className="text-xs text-gray-500 mb-2">Failed</div>
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
          
          {/* Processed Files List */}
          {showProcessed && status.processed_files && status.processed_files.length > 0 && (
            <div className="pt-3 border-t border-white/10">
              <div className="text-xs font-semibold text-emerald-400 mb-2">Processed Files:</div>
              <ul className="space-y-1 max-h-40 overflow-y-auto custom-scrollbar">
                {status.processed_files.map((file, idx) => (
                  <li key={idx} className="text-xs text-gray-400 pl-4 truncate" title={file}>
                    • {file}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Skipped Files List */}
          {showSkipped && status.skipped_files && status.skipped_files.length > 0 && (
            <div className="pt-3 border-t border-white/10">
              <div className="text-xs font-semibold text-amber-400 mb-2">Skipped Files:</div>
              <ul className="space-y-1 max-h-40 overflow-y-auto custom-scrollbar">
                {status.skipped_files.map((file, idx) => (
                  <li key={idx} className="text-xs text-gray-400 pl-4 truncate" title={file}>
                    • {file}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Failed Files List */}
          {showFailed && status.failed_files && status.failed_files.length > 0 && (
            <div className="pt-3 border-t border-white/10">
              <div className="text-xs font-semibold text-red-400 mb-2">Failed Files:</div>
              <ul className="space-y-2 max-h-40 overflow-y-auto custom-scrollbar">
                {status.failed_files.map((item, idx) => (
                  <li key={idx} className="text-xs text-gray-400 pl-4">
                    <div className="text-gray-300 truncate" title={item.file}>• {item.file}</div>
                    <div className="text-red-400 pl-2 mt-1">{item.error}</div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
