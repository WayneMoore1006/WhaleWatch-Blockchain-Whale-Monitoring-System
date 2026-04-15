import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { TableSkeleton } from '../components/Skeleton';

const API = 'http://localhost:8000';
const CHAINS = ['All', 'ETH', 'BSC', 'SOL'];

const Watchlist: React.FC = () => {
  const navigate = useNavigate();
  const [wallets, setWallets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterChain, setFilterChain] = useState('All');
  const [showAddModal, setShowAddModal] = useState(false);
  const [addAddress, setAddAddress] = useState('');
  const [addLabel, setAddLabel] = useState('');
  const [addChainHint, setAddChainHint] = useState('');
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [addResult, setAddResult] = useState<any>(null);
  const [maskedMap, setMaskedMap] = useState<Record<number, boolean>>({});
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [draggedIdx, setDraggedIdx] = useState<number | null>(null);

  const fetchWallets = useCallback(async () => {
    try {
      const chain = filterChain !== 'All' ? `?chain=${filterChain}` : '';
      const res = await fetch(`${API}/api/watchlist${chain}`);
      const data = await res.json();
      setWallets(Array.isArray(data) ? data : []);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (e) {
      setError('API connection failed. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, [filterChain]);

  useEffect(() => { setLoading(true); fetchWallets(); }, [fetchWallets]);

  const handleAdd = async () => {
    if (!addAddress.trim()) return;
    setAdding(true);
    setAddError(null);
    setAddResult(null);
    try {
      const res = await fetch(`${API}/api/watchlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addAddress.trim(), chain: addChainHint || null, label: addLabel || null })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Add failed');
      setAddResult(data);
      fetchWallets();
      setAddAddress(''); setAddLabel(''); setAddChainHint('');
      setTimeout(() => setShowAddModal(false), 1500);
    } catch (e: any) {
      setAddError(e.message);
    } finally {
      setAdding(false);
    }
  };

  const handleAction = async (wallet: any, action: 'pause' | 'resume' | 'delete' | 'refresh') => {
    try {
      if (action === 'delete') {
        if (!confirm(`Delete ${wallet.label || wallet.address.slice(0, 12)}...?`)) return;
        await fetch(`${API}/api/watchlist/${wallet.id}`, { method: 'DELETE' });
      } else {
        await fetch(`${API}/api/watchlist/${wallet.id}/${action}`, { method: 'POST' });
      }
      fetchWallets();
    } catch (e) { console.error(action, e); }
  };

  const toggleMask = (id: number) => setMaskedMap(m => ({ ...m, [id]: !m[id] }));
  const displayAddr = (w: any) => maskedMap[w.id] ? (w.masked_address || `${w.address.slice(0,6)}...${w.address.slice(-4)}`) : w.address;

  const handleDragStart = (e: React.DragEvent, index: number) => {
    setDraggedIdx(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIdx === null || draggedIdx === index) return;

    const newWallets = [...wallets];
    const draggedItem = newWallets[draggedIdx];
    newWallets.splice(draggedIdx, 1);
    newWallets.splice(index, 0, draggedItem);

    setDraggedIdx(index);
    setWallets(newWallets);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDraggedIdx(null);
    const orders = wallets.map((w, idx) => ({ id: w.id, index: idx }));
    try {
      await fetch(`${API}/api/watchlist/reorder`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ orders })
      });
    } catch (err) {
      console.error('Failed to reorder', err);
    }
  };

  if (loading) return <div className="p-10"><TableSkeleton /></div>;

  const activeCount = wallets.filter(w => w.is_active).length;
  const totalBalanceUsd = wallets.reduce((s, w) => s + (w.native_balance_usd || 0), 0);

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
        <div>
          <h1 className="text-4xl font-headline font-bold tracking-tight text-on-surface">Watchlist</h1>
          <p className="text-on-surface-variant opacity-60 mt-2 text-sm max-w-xl">
            Monitor high-value wallets across ETH, BSC, and SOL.
            {lastUpdated && <span className="ml-2 opacity-60">Updated {lastUpdated}</span>}
          </p>
        </div>
        <button onClick={() => setShowAddModal(true)}
          className="bg-gradient-to-br from-primary to-primary-container text-on-primary-container px-6 py-3 rounded-xl font-headline font-bold text-sm flex items-center gap-2 hover:opacity-90 transition-all shadow-lg shadow-primary/20">
          <span className="material-symbols-outlined text-lg">add</span>Add Wallet
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/10">
          <p className="text-xs text-on-surface-variant uppercase tracking-widest opacity-60 mb-2">Total Tracked</p>
          <p className="text-2xl font-headline font-bold text-on-surface">{wallets.length} <span className="text-sm font-normal opacity-50">Wallets</span></p>
        </div>
        <div className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/10">
          <p className="text-xs text-on-surface-variant uppercase tracking-widest opacity-60 mb-2">Active Monitoring</p>
          <p className="text-2xl font-headline font-bold text-secondary">{activeCount}</p>
        </div>
        <div className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/10">
          <p className="text-xs text-on-surface-variant uppercase tracking-widest opacity-60 mb-2">Est. Total Value</p>
          <p className="text-2xl font-headline font-bold text-primary">
            {totalBalanceUsd > 0 ? `$${totalBalanceUsd.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '--'}
          </p>
        </div>
      </div>

      {/* Error */}
      {error && <div className="mb-4 p-4 rounded-xl bg-tertiary-container/20 text-tertiary text-sm">{error}</div>}

      {/* Chain Filter */}
      <div className="flex items-center gap-2 mb-4">
        {CHAINS.map(c => (
          <button key={c} onClick={() => setFilterChain(c)}
            className={`px-4 py-2 rounded-lg text-sm font-bold transition-colors ${filterChain === c ? 'bg-primary text-on-primary' : 'bg-surface-container-high text-on-surface-variant hover:text-on-surface'}`}>
            {c}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-surface-container-low rounded-2xl overflow-hidden shadow-2xl border border-outline-variant/5">
        {wallets.length === 0 ? (
          <div className="p-16 text-center">
            <span className="material-symbols-outlined text-5xl text-outline mb-4 block">account_balance_wallet</span>
            <p className="text-on-surface-variant">No wallets in watchlist yet.</p>
            <p className="text-outline text-xs mt-1">Click "Add Wallet" to start monitoring.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="text-xs uppercase tracking-widest text-on-surface-variant opacity-50 font-bold border-b border-outline-variant/10">
                  <th className="px-6 py-4">Address</th>
                  <th className="px-6 py-4">Label</th>
                  <th className="px-6 py-4">Chain</th>
                  <th className="px-6 py-4">Balance</th>
                  <th className="px-6 py-4">Synced</th>
                  <th className="px-6 py-4">Alerts</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/5">
                {wallets.map((w, idx) => (
                  <tr 
                    key={w.id} 
                    draggable
                    onDragStart={(e) => handleDragStart(e, idx)}
                    onDragOver={(e) => handleDragOver(e, idx)}
                    onDrop={handleDrop}
                    onClick={() => navigate(`/intelligence/${w.address}`)} 
                    className={`hover:bg-surface-container transition-colors group cursor-pointer ${draggedIdx === idx ? 'opacity-50' : ''}`}
                  >
                    <td className="px-6 py-5">
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-outline text-sm cursor-grab">drag_indicator</span>
                        <span className="font-mono text-sm tracking-tight text-on-surface">{displayAddr(w)}</span>
                        <button onClick={(e) => { e.stopPropagation(); toggleMask(w.id); }}
                          className="opacity-0 group-hover:opacity-100 transition-opacity text-outline hover:text-primary">
                          <span className="material-symbols-outlined text-base">{maskedMap[w.id] ? 'visibility' : 'visibility_off'}</span>
                        </button>
                      </div>
                    </td>
                    <td className="px-6 py-5 text-sm">{w.label || '—'}</td>
                    <td className="px-6 py-5">
                      <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase ${w.chain === 'ETH' ? 'bg-primary/20 text-primary' : w.chain === 'BSC' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-purple-500/20 text-purple-400'}`}>
                        {w.chain}
                      </span>
                    </td>
                    <td className="px-6 py-5 text-sm font-mono">
                      {w.native_balance != null ? `${Number(w.native_balance).toFixed(4)} ${w.native_symbol || ''}` : '--'}
                      {w.native_balance_usd && <span className="block text-[10px] text-outline">${w.native_balance_usd.toLocaleString()}</span>}
                    </td>
                    <td className="px-6 py-5 text-xs text-outline">
                      {w.last_synced_at ? new Date(w.last_synced_at).toLocaleString() : 'Never'}
                    </td>
                    <td className="px-6 py-5">
                      {w.alert_count > 0 ? (
                        <span className="px-2 py-0.5 rounded-full bg-tertiary-container/30 text-tertiary text-xs font-bold">{w.alert_count}</span>
                      ) : <span className="text-outline text-xs">0</span>}
                    </td>
                    <td className="px-6 py-5">
                      <span className={`px-2 py-1 rounded-full text-[10px] font-bold ${w.is_active ? 'bg-secondary/20 text-secondary' : 'bg-outline-variant/30 text-outline'}`}>
                        {w.is_active ? 'Active' : 'Paused'}
                      </span>
                    </td>
                    <td className="px-6 py-5">
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <ActionBtn icon="refresh" title="Refresh" onClick={() => handleAction(w, 'refresh')} />
                        {w.is_active
                          ? <ActionBtn icon="pause" title="Pause" onClick={() => handleAction(w, 'pause')} />
                          : <ActionBtn icon="play_arrow" title="Resume" onClick={() => handleAction(w, 'resume')} />}
                        <ActionBtn icon="delete" title="Delete" onClick={() => handleAction(w, 'delete')} danger />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setShowAddModal(false)}>
          <div className="bg-surface-container-low rounded-2xl p-8 w-full max-w-md border border-outline-variant/20" onClick={e => e.stopPropagation()}>
            <h2 className="text-xl font-headline font-bold mb-6">Add Wallet to Watchlist</h2>

            <label className="block text-xs uppercase tracking-widest text-outline mb-2">Wallet Address *</label>
            <input value={addAddress} onChange={e => setAddAddress(e.target.value)}
              placeholder="0x... or Solana base58"
              className="w-full bg-surface-container p-3 rounded-xl text-sm font-mono border border-outline-variant/20 focus:border-primary outline-none mb-4" />

            <label className="block text-xs uppercase tracking-widest text-outline mb-2">Label (optional)</label>
            <input value={addLabel} onChange={e => setAddLabel(e.target.value)}
              placeholder="e.g. Whale, MEV Bot..."
              className="w-full bg-surface-container p-3 rounded-xl text-sm border border-outline-variant/20 focus:border-primary outline-none mb-4" />

            <label className="block text-xs uppercase tracking-widest text-outline mb-2">Chain Hint (optional — auto-detect if empty)</label>
            <div className="flex gap-2 mb-6">
              {['', 'ETH', 'BSC', 'SOL'].map(c => (
                <button key={c}
                  onClick={() => setAddChainHint(c)}
                  className={`px-3 py-2 rounded-lg text-xs font-bold transition-colors ${addChainHint === c ? 'bg-primary text-on-primary' : 'bg-surface-container-high text-on-surface-variant'}`}>
                  {c || 'Auto'}
                </button>
              ))}
            </div>

            {addError && <p className="text-tertiary text-sm mb-4">⚠ {addError}</p>}
            {addResult && (
              <div className="mb-4 p-3 rounded-xl bg-secondary/10 text-secondary text-sm">
                ✓ Added! Chain detected: <b>{addResult.chain_detection?.chain}</b>
                {addResult.chain_detection?.ambiguous && ' (ambiguous — please verify)'}
              </div>
            )}

            <div className="flex gap-3">
              <button onClick={() => setShowAddModal(false)}
                className="flex-1 py-3 rounded-xl bg-surface-container-high text-on-surface-variant font-bold text-sm">Cancel</button>
              <button onClick={handleAdd} disabled={adding || !addAddress.trim()}
                className="flex-1 py-3 rounded-xl bg-primary text-on-primary font-bold text-sm disabled:opacity-50">
                {adding ? 'Adding...' : 'Add & Sync'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const ActionBtn = ({ icon, title, onClick, danger }: any) => (
  <button title={title} onClick={(e) => { e.stopPropagation(); onClick(); }}
    className={`p-1.5 rounded-lg transition-colors ${danger ? 'hover:bg-tertiary/20 hover:text-tertiary text-outline' : 'hover:bg-primary/20 hover:text-primary text-outline'}`}>
    <span className="material-symbols-outlined text-base">{icon}</span>
  </button>
);

export default Watchlist;
