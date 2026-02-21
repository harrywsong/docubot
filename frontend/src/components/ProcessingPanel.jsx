import { useState, useEffect, useRef } from 'react';
import { startProcessing, connectProcessingStream } from '../api';

export default function ProcessingPanel({ onToast }) {
  const [processing, setProcessing] = useState(false);
  const [status, setStatus] = useState({
    processed: 0,
    skipped: 0,
    failed: 0,
    failed_files: []
  });
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
      setStatus({ processed: 0, skipped: 0, failed: 0, failed_files: [] });
      
      // Connect to WebSocket for real-time updates
      wsRef.current = connectProcessingStream(
        (data) => {
          if (data.type === 'status') {
            setStatus({
              processed: data.processed,
              skipped: data.skipped,
              failed: data.failed,
              failed_files: []
            });
            setProcessing(data.is_processing);
          } else if (data.type === 'complete') {
            setStatus({
              processed: data.processed,
              skipped: data.skipped,
              failed: data.failed,
              failed_files: data.failed_files || []
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

  return (
    <div className="processing-section">
      <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>
        Document Processing
      </h3>
      
      <button
        className="process-btn"
        onClick={handleStartProcessing}
        disabled={processing}
      >
        {processing ? (
          <>
            <span className="loading" style={{ marginRight: '8px' }}></span>
            Processing...
          </>
        ) : (
          'Process Documents'
        )}
      </button>

      {(processing || status.processed > 0 || status.skipped > 0 || status.failed > 0) && (
        <div className="processing-status">
          <p><strong>Processed:</strong> {status.processed}</p>
          <p><strong>Skipped:</strong> {status.skipped}</p>
          <p><strong>Failed:</strong> {status.failed}</p>
          
          {status.failed_files && status.failed_files.length > 0 && (
            <div className="error">
              <strong>Failed files:</strong>
              <ul style={{ marginTop: '4px', marginLeft: '20px' }}>
                {status.failed_files.map((item, idx) => (
                  <li key={idx}>
                    {item.file}: {item.error}
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
