import React, { useState, useEffect, useCallback } from 'react';

const API = 'http://localhost:8000';
const SEVERITY_COLORS: Record<string, string> = {
  high:   'bg-tertiary-container/30 text-tertiary border-tertiary/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low:    'bg-primary-container/20 text-primary border-primary/20'
};
const SEVERITY_ICON: Record<string, string> = {
  high: 'warning', medium: 'info', low: 'notifications'
};

const AlertsCenter: React.FC = () => {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterChain, setFilterChain] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('');
  const [filterSource, setFilterSource] = useState('');
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchAlerts = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (filterChain) params.append('chain', filterChain);
      if (filterSeverity) params.append('severity', filterSeverity);
      if (filterSource) params.append('source', filterSource);
      params.append('limit', '100');

      const res = await fetch(`${API}/api/alerts?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setAlerts(Array.isArray(data) ? data : []);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (e) {
      setError('Failed to load alerts. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, [filterChain, filterSeverity, filterSource]);

  useEffect(() => { setLoading(true); fetchAlerts(); }, [fetchAlerts]);

  const markRead = async (id: number) => {
    await fetch(`${API}/api/alerts/${id}/read`, { method: 'PATCH' });
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, status: 'read' } : a));
    window.dispatchEvent(new Event('alertsUpdated'));
  };

  const archiveAlert = async (id: number) => {
    await fetch(`${API}/api/alerts/${id}/archive`, { method: 'PATCH' });
    setAlerts(prev => prev.filter(a => a.id !== id));
    window.dispatchEvent(new Event('alertsUpdated'));
  };

  const triggerRebuild = async () => {
    await fetch(`${API}/api/alerts/rebuild`, { method: 'POST' });
    setTimeout(() => { fetchAlerts(); window.dispatchEvent(new Event('alertsUpdated')); }, 500);
  };

  const triggerExternalSync = async () => {
    await fetch(`${API}/api/external-alerts/sync`, { method: 'POST' });
    setTimeout(() => { fetchAlerts(); window.dispatchEvent(new Event('alertsUpdated')); }, 1000);
  };

  const newCount = alerts.filter(a => a.status === 'new').length;
  const highCount = alerts.filter(a => a.severity === 'high').length;
  const externalCount = alerts.filter(a => a.source === 'external').length;

  const FilterBtn = ({ label, value, field, setState }: any) => {
    const current = field === 'chain' ? filterChain : field === 'severity' ? filterSeverity : filterSource;
    return (
      <button onClick={() => setState(current === value ? '' : value)}
        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${current === value ? 'bg-primary text-on-primary' : 'bg-surface-container-high text-on-surface-variant hover:text-on-surface'}`}>
        {label}
      </button>
    );
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header Section */}
      <section className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-8">
        <div className="lg:col-span-2 p-8 rounded-2xl bg-surface-container relative overflow-hidden flex flex-col justify-between min-h-[160px]">
          <div className="relative z-10">
            <h1 className="text-4xl font-bold font-headline tracking-tighter text-on-surface mb-2">Alerts Center</h1>
            <p className="text-on-surface-variant text-sm max-w-sm">
              On-chain anomaly detection — ETH, BSC, SOL
              {lastUpdated && <span className="ml-2 opacity-50">· {lastUpdated}</span>}
            </p>
          </div>
          <div className="absolute right-0 bottom-0 opacity-10">
            <span className="material-symbols-outlined text-[120px]" style={{ fontVariationSettings: "'FILL' 1" }}>notifications_active</span>
          </div>
        </div>
        <div className="p-6 rounded-2xl bg-surface-container flex flex-col justify-center border-l-4 border-tertiary">
          <span className="text-[10px] text-on-surface-variant uppercase tracking-widest mb-1">New Alerts</span>
          <span className="text-3xl font-headline font-bold text-tertiary">{loading ? '--' : newCount}</span>
          <span className="text-xs text-tertiary mt-1">{highCount} high severity</span>
        </div>
        <div className="p-6 rounded-2xl bg-surface-container flex flex-col justify-center border-l-4 border-secondary">
          <span className="text-[10px] text-on-surface-variant uppercase tracking-widest mb-1">External Signals</span>
          <span className="text-3xl font-headline font-bold text-secondary">{loading ? '--' : externalCount}</span>
          <span className="text-xs text-secondary mt-1">from public sources</span>
        </div>
      </section>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 rounded-xl bg-tertiary-container/20 text-tertiary text-sm flex items-center gap-2">
          <span className="material-symbols-outlined">warning</span>{error}
        </div>
      )}

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="flex items-center gap-2">
          <span className="text-xs text-outline uppercase tracking-widest">Chain:</span>
          {['ETH', 'BSC', 'SOL'].map(c => (
            <FilterBtn key={c} label={c} value={c} field="chain" setState={setFilterChain} />
          ))}
        </div>
        <div className="w-px h-5 bg-outline-variant/30" />
        <div className="flex items-center gap-2">
          <span className="text-xs text-outline uppercase tracking-widest">Severity:</span>
          {['high', 'medium', 'low'].map(s => (
            <FilterBtn key={s} label={s.charAt(0).toUpperCase() + s.slice(1)} value={s} field="severity" setState={setFilterSeverity} />
          ))}
        </div>
        <div className="w-px h-5 bg-outline-variant/30" />
        <div className="flex items-center gap-2">
          <span className="text-xs text-outline uppercase tracking-widest">Source:</span>
          {['watchlist', 'external'].map(s => (
            <FilterBtn key={s} label={s.charAt(0).toUpperCase() + s.slice(1)} value={s} field="source" setState={setFilterSource} />
          ))}
        </div>
        <div className="ml-auto flex gap-2">
          <button onClick={triggerRebuild}
            className="px-3 py-2 rounded-lg bg-surface-container-high text-on-surface-variant hover:text-on-surface text-xs font-bold flex items-center gap-1 transition-colors">
            <span className="material-symbols-outlined text-sm">refresh</span>Rebuild Alerts
          </button>
          <button onClick={triggerExternalSync}
            className="px-3 py-2 rounded-lg bg-surface-container-high text-on-surface-variant hover:text-on-surface text-xs font-bold flex items-center gap-1 transition-colors">
            <span className="material-symbols-outlined text-sm">cloud_sync</span>Sync External
          </button>
        </div>
      </div>

      {/* Alert List */}
      <section className="space-y-3">
        {loading ? (
          [1, 2, 3].map(i => <div key={i} className="h-24 bg-surface-container-low rounded-2xl animate-pulse" />)
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 rounded-2xl bg-surface-container-low">
            <span className="material-symbols-outlined text-5xl text-outline mb-4 opacity-30" style={{ fontVariationSettings: "'FILL' 1" }}>notifications_off</span>
            <p className="text-on-surface-variant">No alerts found.</p>
            <p className="text-outline text-xs mt-1">
              {filterChain || filterSeverity || filterSource ? 'Try clearing filters.' : 'Wallets will generate alerts after syncing.'}
            </p>
          </div>
        ) : alerts.map(alert => (
          <div key={alert.id}
            className={`group relative bg-surface-container-low hover:bg-surface-container transition-all duration-300 rounded-2xl p-5 border-l-2 overflow-hidden ${alert.status === 'read' ? 'opacity-60 border-outline-variant/30' : SEVERITY_COLORS[alert.severity || 'low']}`}>
            <div className="flex items-start gap-4">
              <div className={`p-3 rounded-xl ${SEVERITY_COLORS[alert.severity || 'low']} border flex-shrink-0`}>
                <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>
                  {SEVERITY_ICON[alert.severity || 'low']}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1 gap-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-headline font-bold text-on-surface text-sm">
                      {alert.title || alert.alert_type}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${SEVERITY_COLORS[alert.severity || 'low']}`}>
                      {alert.severity}
                    </span>
                    {alert.source === 'external' && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-outline/10 text-outline border border-outline-variant/30">
                        External
                      </span>
                    )}
                    {alert.chain && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-surface-container text-outline">
                        {alert.chain}
                      </span>
                    )}
                  </div>
                  <span className="text-[11px] text-on-surface-variant flex-shrink-0">
                    {alert.created_at ? new Date(alert.created_at).toLocaleString() : '--'}
                  </span>
                </div>
                <p className="text-sm text-on-surface mb-3 leading-relaxed">{alert.description}</p>
                {alert.wallet_address && (
                  <p className="text-[10px] font-mono text-outline mb-2">
                    Wallet: {alert.wallet_address.slice(0, 10)}...{alert.wallet_address.slice(-6)}
                  </p>
                )}
                <div className="flex items-center gap-3">
                  {alert.status === 'new' && (
                    <button onClick={() => markRead(alert.id)}
                      className="text-[10px] font-bold text-outline hover:text-on-surface flex items-center gap-1 transition-colors">
                      <span className="material-symbols-outlined text-sm">done</span>Mark Read
                    </button>
                  )}
                  <button onClick={() => archiveAlert(alert.id)}
                    className="text-[10px] font-bold text-outline hover:text-tertiary flex items-center gap-1 transition-colors">
                    <span className="material-symbols-outlined text-sm">archive</span>Archive
                  </button>
                  {alert.related_tx_hash && (
                    <span className="text-[10px] font-mono text-outline">
                      Tx: {alert.related_tx_hash.slice(0, 12)}...
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
};

export default AlertsCenter;
