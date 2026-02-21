import { useState, useEffect } from 'react';
import { checkHealth } from '../api';

export default function HealthCheck() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    performHealthCheck();
  }, []);

  async function performHealthCheck() {
    setLoading(true);
    try {
      const response = await checkHealth();
      setHealth(response);
    } catch (error) {
      setHealth({
        status: 'error',
        errors: [`Failed to check health: ${error.message}`]
      });
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="health-status" style={{ background: '#f8f9fa' }}>
        Checking system health...
      </div>
    );
  }

  if (!health || health.status === 'error') {
    return (
      <div className="health-status unhealthy">
        <strong>⚠️ System Error</strong>
        {health?.errors && health.errors.length > 0 && (
          <ul>
            {health.errors.map((error, idx) => (
              <li key={idx}>{error}</li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  if (health.status === 'unhealthy') {
    return (
      <div className="health-status unhealthy">
        <strong>⚠️ System Not Ready</strong>
        {health.errors && health.errors.length > 0 && (
          <ul>
            {health.errors.map((error, idx) => (
              <li key={idx}>{error}</li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  if (health.status === 'healthy') {
    return (
      <div className="health-status healthy">
        <strong>✓ System Ready</strong>
        <p style={{ marginTop: '4px', fontSize: '13px' }}>
          All systems operational
        </p>
      </div>
    );
  }

  return null;
}
