import { CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

export default function HealthCheck({ status }) {
  if (!status) {
    return (
      <div className="flex items-center gap-2 text-foreground-muted text-sm">
        <div className="w-2 h-2 rounded-full bg-foreground-muted animate-pulse" />
        <span>Checking status...</span>
      </div>
    );
  }

  const isHealthy = status.status === 'healthy';
  const Icon = isHealthy ? CheckCircle2 : status.status === 'degraded' ? AlertCircle : XCircle;
  const color = isHealthy ? 'text-green-400' : status.status === 'degraded' ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Icon className={`w-4 h-4 ${color}`} />
        <span className="text-sm font-medium text-foreground">
          {isHealthy ? 'System Healthy' : status.status === 'degraded' ? 'Degraded' : 'Unhealthy'}
        </span>
      </div>
      
      {status.details && (
        <div className="text-xs text-foreground-muted space-y-1">
          {status.details.ollama_status && (
            <div className="flex items-center justify-between">
              <span>Ollama:</span>
              <span className={status.details.ollama_status === 'available' ? 'text-green-400' : 'text-red-400'}>
                {status.details.ollama_status}
              </span>
            </div>
          )}
          {status.details.vector_store_documents !== undefined && (
            <div className="flex items-center justify-between">
              <span>Documents:</span>
              <span className="text-foreground">{status.details.vector_store_documents}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
