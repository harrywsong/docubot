import { useEffect } from 'react';
import { CheckCircle2, AlertCircle, Info, XCircle } from 'lucide-react';

export default function Toast({ message, type = 'info', onClose, duration = 3000 }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, duration);

    return () => clearTimeout(timer);
  }, [onClose, duration]);

  const icons = {
    success: <CheckCircle2 className="w-5 h-5" />,
    error: <XCircle className="w-5 h-5" />,
    warning: <AlertCircle className="w-5 h-5" />,
    info: <Info className="w-5 h-5" />
  };

  const styles = {
    success: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
    error: 'bg-red-500/10 border-red-500/20 text-red-400',
    warning: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
    info: 'bg-blue-500/10 border-blue-500/20 text-blue-400'
  };

  return (
    <div className={`
      fixed top-4 right-4 z-50
      glass-card
      px-4 py-3 rounded-xl
      border ${styles[type]}
      flex items-center gap-3
      animate-slide-in
      shadow-glow
      backdrop-blur-xl
    `}>
      {icons[type]}
      <span className="text-sm font-medium">{message}</span>
    </div>
  );
}
