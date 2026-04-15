import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import { WalletDetailSkeleton } from '../components/Skeleton';

const API = 'http://localhost:8000';

const fmt = (v: number | null | undefined, decimals = 4) =>
  v != null ? Number(v).toFixed(decimals) : '--';
const fmtUSD = (v: number | null | undefined) =>
  v != null ? `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}` : 'N/A';

const COLORS = ['#8A2BE2', '#4169E1', '#00CED1', '#32CD32', '#FFD700', '#FF8C00', '#FF1493'];

const getTxTypeColor = (type: string) => {
  switch (type) {
    case 'approve': return 'bg-yellow-500/20 text-yellow-500';
    case 'swap': return 'bg-purple-500/20 text-purple-400';
    case 'buy': return 'bg-green-500/20 text-green-400';
    case 'sell': return 'bg-red-500/20 text-red-400';
    case 'contract_interaction': return 'bg-blue-500/20 text-blue-400';
    default: return 'bg-surface-container-high text-outline';
  }
};

const WalletIntelligence: React.FC = () => {
  const { address: urlAddress } = useParams<{ address: string }>();
  const navigate = useNavigate();

  const [searchInput, setSearchInput] = useState(urlAddress || '');
  const [queriedAddress, setQueriedAddress] = useState(urlAddress || '');
  const [chainHint, setChainHint] = useState('');
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [isMasked, setIsMasked] = useState(false);
  // 'idle' | 'syncing_background' | 'fresh'
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing_background' | 'fresh'>('idle');

  const analyze = useCallback(async (addr: string, chain?: string) => {
    if (!addr.trim()) return;
    setAnalyzing(true);
    setError(null);
    setSyncStatus('idle');
    try {
      const res = await fetch(`${API}/api/wallet-intelligence/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr.trim(), chain: chain || null })
      });
      const result = await res.json();
      if (!res.ok) throw new Error(result.detail || 'Analysis failed');
      setData(result);
      setQueriedAddress(addr.trim());
      navigate(`/intelligence/${addr.trim()}`, { replace: true });
      // 若後端告知資料是過期快取，顯示背景同步指示
      if (result.sync_status === 'stale') {
        setSyncStatus('syncing_background');
      } else {
        setSyncStatus('fresh');
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setAnalyzing(false);
    }
  }, [navigate]);

  // 若 URL 有地址則自動分析
  useEffect(() => {
    if (urlAddress) { 
      setSearchInput(urlAddress);
      analyze(urlAddress); 
    }
  }, [urlAddress, analyze]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    analyze(searchInput, chainHint || undefined);
  };

  // 智慧輪詢：當處於背景同步中，定期檢查更新
  useEffect(() => {
    let interval: any;
    if (syncStatus === 'syncing_background' && queriedAddress) {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`${API}/api/wallet-intelligence/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ address: queriedAddress, chain: data?.chain || null })
          });
          const result = await res.json();
          if (res.ok && result.sync_status === 'fresh') {
            setData(result);
            setSyncStatus('fresh');
          }
        } catch (e) {
          console.error("Polling failed:", e);
        }
      }, 5000); // 每 5 秒檢查一次
    }
    return () => { if (interval) clearInterval(interval); };
  }, [syncStatus, queriedAddress, data?.chain]);

  const addToWatchlist = async () => {
    if (!queriedAddress) return;
    try {
      await fetch(`${API}/api/watchlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: queriedAddress, chain: data?.chain || null })
      });
      alert('Added to watchlist!');
    } catch (e) { alert('Failed to add.'); }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Search Bar */}
      <div className="mb-8">
        <h1 className="text-3xl font-headline font-bold tracking-tight text-on-surface mb-6">Wallet Intelligence</h1>
        <form onSubmit={handleSearch} className="flex gap-3">
          <input
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            placeholder="Enter ETH / BSC / SOL address..."
            className="flex-1 bg-surface-container-low p-4 rounded-xl text-sm font-mono border border-outline-variant/20 focus:border-primary outline-none"
          />
          <select value={chainHint} onChange={e => setChainHint(e.target.value)}
            className="bg-surface-container-low px-3 py-4 rounded-xl text-sm border border-outline-variant/20 focus:border-primary outline-none">
            <option value="">Auto-detect chain</option>
            <option value="ETH">ETH</option>
            <option value="BSC">BSC</option>
            <option value="SOL">SOL</option>
          </select>
          <button type="submit" disabled={analyzing || !searchInput.trim()}
            className="px-6 py-4 bg-primary text-on-primary rounded-xl font-bold text-sm disabled:opacity-50 flex items-center gap-2">
            {analyzing ? <span className="animate-spin material-symbols-outlined text-lg">autorenew</span> : <span className="material-symbols-outlined text-lg">search</span>}
            {analyzing ? 'Analyzing...' : 'Analyze'}
          </button>
        </form>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 rounded-xl bg-tertiary-container/20 text-tertiary text-sm flex items-center gap-2">
          <span className="material-symbols-outlined">warning</span>{error}
        </div>
      )}

      {/* Loading */}
      {analyzing && <div className="p-10"><WalletDetailSkeleton /></div>}

      {/* Results */}
      {!analyzing && data && (
        <div>
          {/* Background Sync Banner */}
          {syncStatus === 'syncing_background' && (
            <div className="mb-5 flex items-center gap-3 px-4 py-3 rounded-xl bg-primary/10 border border-primary/20 text-sm text-primary animate-pulse">
              <span className="animate-spin material-symbols-outlined text-base">autorenew</span>
              <span>Showing cached data — updating on-chain data in background...</span>
            </div>
          )}
          {syncStatus === 'fresh' && data.sync_status === 'stale' && (
            <div className="mb-5 flex items-center gap-3 px-4 py-3 rounded-xl bg-secondary/10 border border-secondary/20 text-sm text-secondary">
              <span className="material-symbols-outlined text-base">check_circle</span>
              <span>Background sync complete. Refresh to see latest data.</span>
            </div>
          )}
          {/* Summary Section */}
          <section className="mb-8">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <span className={`px-2 py-0.5 rounded bg-primary-container text-on-primary-container text-[10px] font-bold uppercase tracking-wider`}>
                    {data.chain}
                  </span>
                  {data.is_in_watchlist && (
                    <span className="px-2 py-0.5 rounded bg-secondary-container text-on-secondary-container text-[10px] font-bold uppercase">
                      In Watchlist
                    </span>
                  )}
                  {data.chain_detection?.ambiguous && (
                    <span className="px-2 py-0.5 rounded bg-tertiary-container text-on-tertiary-container text-[10px] font-bold uppercase">
                      EVM Ambiguous
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="text-lg md:text-xl font-headline font-bold tracking-tight text-on-surface break-all font-mono">
                    {isMasked ? `${data.address.slice(0, 6)}...${data.address.slice(-4)}` : data.address}
                  </h2>
                  <button onClick={() => setIsMasked(!isMasked)}
                    className="w-9 h-9 rounded-xl bg-surface-container-high flex items-center justify-center hover:bg-surface-container-highest">
                    <span className="material-symbols-outlined text-outline text-base">{isMasked ? 'visibility' : 'visibility_off'}</span>
                  </button>
                  <button onClick={() => navigator.clipboard.writeText(data.address)}
                    className="w-9 h-9 rounded-xl bg-surface-container-high flex items-center justify-center hover:bg-surface-container-highest">
                    <span className="material-symbols-outlined text-primary text-base">content_copy</span>
                  </button>
                </div>
                {data.label && <p className="text-sm text-outline mt-1">{data.label}</p>}
              </div>
              <div className="flex gap-3">
                {!data.is_in_watchlist && (
                  <button onClick={addToWatchlist}
                    className="flex items-center gap-2 px-4 py-2 bg-surface-container-high text-on-surface rounded-xl font-bold text-sm hover:bg-surface-container-highest">
                    <span className="material-symbols-outlined text-sm">bookmark_add</span>Watch
                  </button>
                )}
              </div>
            </div>
            {data.last_synced_at && (
              <p className="text-xs text-outline mt-3">
                Last synced: {new Date(data.last_synced_at).toLocaleString()} · Source: {data.data_source}
              </p>
            )}
          </section>

          {/* Balance & Flow Cards */}
          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            <div className="p-6 rounded-2xl bg-surface-container border-l-4 border-primary">
              <p className="text-on-surface-variant text-xs uppercase tracking-widest font-label mb-2">Native Balance</p>
              <h3 className="text-2xl font-headline font-bold text-on-surface">
                {data.balance?.native_balance != null ? `${fmt(data.balance.native_balance)} ${data.balance.native_symbol}` : 'No data yet'}
              </h3>
              <p className="text-sm text-outline mt-1">
                {data.balance?.native_balance_usd != null ? fmtUSD(data.balance.native_balance_usd) : 'Price unavailable'}
              </p>
            </div>
            <div className="p-6 rounded-2xl bg-surface-container border-l-4 border-secondary">
              <p className="text-on-surface-variant text-xs uppercase tracking-widest font-label mb-2">Est. Total Value</p>
              <h3 className="text-2xl font-headline font-bold text-secondary">
                {data.balance?.total_estimated_usd != null ? fmtUSD(data.balance.total_estimated_usd) : 'N/A'}
              </h3>
              <p className="text-xs text-outline mt-1">
                {data.balance?.price_source ? `via ${data.balance.price_source}` : 'Price source unavailable'}
              </p>
            </div>
            <div className="p-6 rounded-2xl bg-surface-container border-l-4 border-tertiary">
              <p className="text-on-surface-variant text-xs uppercase tracking-widest font-label mb-2">30d Net Flow</p>
              <h3 className={`text-2xl font-headline font-bold ${(data.flow_30d?.netflow_usd || 0) >= 0 ? 'text-secondary' : 'text-tertiary'}`}>
                {data.flow_30d ? fmtUSD(data.flow_30d.netflow_usd) : 'N/A'}
              </h3>
              {data.flow_30d && (
                <p className="text-xs text-outline mt-1">
                  In: {fmtUSD(data.flow_30d.inflow_usd)} · Out: {fmtUSD(data.flow_30d.outflow_usd)}
                </p>
              )}
            </div>
          </section>

          {/* Activity Info */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { label: 'First Active', value: data.first_active ? new Date(data.first_active).toLocaleDateString() : 'N/A' },
              { label: 'Last Active', value: data.last_active ? new Date(data.last_active).toLocaleString() : 'N/A' },
              { label: 'Risk Level', value: data.risk_signals?.level?.toUpperCase() || 'N/A' },
              { label: 'Win Rate', value: data.pnl?.win_rate != null ? `${data.pnl.win_rate}%` : 'N/A' }
            ].map(({ label, value }) => (
              <div key={label} className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/10">
                <p className="text-[10px] uppercase tracking-widest text-outline mb-1">{label}</p>
                <p className="text-sm font-bold text-on-surface">{value}</p>
              </div>
            ))}
          </div>
          {data.risk_signals?.reason && (
            <p className="text-xs text-outline mb-6">Risk signal: {data.risk_signals.reason}</p>
          )}

          {/* Performance & PnL */}
          <section className="mb-8">
            <h2 className="font-headline font-bold text-lg mb-4">Performance Estimates</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
               <div className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/10">
                 <p className="text-[10px] uppercase tracking-widest text-outline mb-1">Unrealized PnL</p>
                 <p className={`text-sm font-bold ${(data.pnl?.unrealized_pnl_usd || 0) >= 0 ? 'text-secondary' : 'text-tertiary'}`}>
                   {data.pnl?.unrealized_pnl_usd != null ? fmtUSD(data.pnl.unrealized_pnl_usd) : 'N/A'}
                 </p>
               </div>
               <div className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/10">
                 <p className="text-[10px] uppercase tracking-widest text-outline mb-1">Realized PnL</p>
                 <p className={`text-sm font-bold ${(data.pnl?.realized_pnl_usd || 0) >= 0 ? 'text-secondary' : 'text-tertiary'}`}>
                   {data.pnl?.realized_pnl_usd != null ? fmtUSD(data.pnl.realized_pnl_usd) : 'N/A'}
                 </p>
               </div>
               <div className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/10">
                 <p className="text-[10px] uppercase tracking-widest text-outline mb-1">7d PnL Proxy</p>
                 <p className={`text-sm font-bold ${(data.pnl?.periods?.['7d'] || 0) >= 0 ? 'text-secondary' : 'text-tertiary'}`}>
                   {data.pnl?.periods?.['7d'] != null ? fmtUSD(data.pnl.periods['7d']) : 'N/A'}
                 </p>
               </div>
               <div className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/10">
                 <p className="text-[10px] uppercase tracking-widest text-outline mb-1">30d PnL Proxy</p>
                 <p className={`text-sm font-bold ${(data.pnl?.periods?.['30d'] || 0) >= 0 ? 'text-secondary' : 'text-tertiary'}`}>
                   {data.pnl?.periods?.['30d'] != null ? fmtUSD(data.pnl.periods['30d']) : 'N/A'}
                 </p>
               </div>
            </div>
          </section>

          {/* Charts Section */}
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div className="bg-surface-container p-6 rounded-3xl border border-outline-variant/10 w-full h-80 flex flex-col">
              <h2 className="font-headline font-bold text-lg mb-4">Volume Trend (30d)</h2>
              <div className="flex-1 min-h-0">
                {data.chart_data?.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data.chart_data}>
                      <defs>
                        <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#8A2BE2" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#8A2BE2" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#424754" vertical={false} opacity={0.2} />
                      <XAxis dataKey="date" stroke="#8c909f" fontSize={10} tickFormatter={(v) => v.slice(5, 10)} />
                      <YAxis hide />
                      <Tooltip contentStyle={{ backgroundColor: '#1f2022', border: '1px solid #424754', borderRadius: '8px' }} />
                      <Area type="monotone" dataKey="tx_count" stroke="#8A2BE2" fillOpacity={1} fill="url(#colorCount)" name="Txs" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center opacity-30 text-sm">No trend data</div>
                )}
              </div>
            </div>
            
            <div className="bg-surface-container p-6 rounded-3xl border border-outline-variant/10 w-full h-80 flex flex-col">
              <h2 className="font-headline font-bold text-lg mb-4">Portfolio Allocation</h2>
              <div className="flex-1 min-h-0">
                {data.holdings?.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={data.holdings} dataKey="estimated_usd" nameKey="token_symbol" cx="50%" cy="50%" outerRadius={80} fill="#8884d8">
                        {data.holdings.map((_: any, index: number) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value: any) => fmtUSD(value)} contentStyle={{ backgroundColor: '#1f2022', border: 'none', borderRadius: '8px' }} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center opacity-30 text-sm">No portfolio data</div>
                )}
              </div>
            </div>
          </section>
          {data.holdings?.length > 0 && (
            <section className="bg-surface-container rounded-3xl overflow-hidden mb-8">
              <div className="px-6 py-5 border-b border-outline-variant/10">
                <h2 className="font-headline font-bold text-lg">Token Holdings</h2>
              </div>
              <table className="w-full text-left border-collapse">
                <thead className="bg-surface-container-low text-[10px] uppercase tracking-widest text-on-surface-variant font-bold">
                  <tr>
                    <th className="px-6 py-3">Token</th>
                    <th className="px-6 py-3">Amount</th>
                    <th className="px-6 py-3 text-right">Value (USD)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/10">
                  {data.holdings.map((h: any, i: number) => (
                    <tr key={i} className="hover:bg-surface-container-high transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                            <span className="material-symbols-outlined text-primary text-sm">token</span>
                          </div>
                          <div>
                            <div className="font-bold text-sm text-on-surface">{h.token_name || h.token_symbol}</div>
                            <div className="text-[10px] text-outline font-bold">{h.token_symbol}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm font-mono">{fmt(h.amount, 2)}</td>
                      <td className="px-6 py-4 text-sm font-bold text-right">
                        {h.estimated_usd != null ? fmtUSD(h.estimated_usd) : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {/* Recent Transactions */}
          <section className="bg-surface-container rounded-3xl overflow-hidden mb-8">
            <div className="px-6 py-5 border-b border-outline-variant/10">
              <h2 className="font-headline font-bold text-lg">Recent Transactions</h2>
            </div>
            {data.recent_transactions?.length > 0 ? (
              <table className="w-full text-left border-collapse">
                <thead className="bg-surface-container-low text-[10px] uppercase tracking-widest text-on-surface-variant font-bold">
                  <tr>
                    <th className="px-6 py-3">Direction</th>
                    <th className="px-6 py-3">Asset</th>
                    <th className="px-6 py-3">Type</th>
                    <th className="px-6 py-3">Amount</th>
                    <th className="px-6 py-3">USD Value</th>
                    <th className="px-6 py-3">Counterparty</th>
                    <th className="px-6 py-3">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/10">
                  {data.recent_transactions.map((tx: any, i: number) => (
                    <tr key={i} className="hover:bg-surface-container-high transition-colors">
                      <td className="px-6 py-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${tx.direction === 'in' ? 'bg-secondary/20 text-secondary' : 'bg-tertiary/20 text-tertiary'}`}>
                          {tx.direction === 'in' ? '↓ IN' : '↑ OUT'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm font-mono">{tx.asset_symbol || '--'}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${getTxTypeColor(tx.tx_type)}`}>
                          {tx.tx_type || 'unknown'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm">{fmt(tx.amount)}</td>
                      <td className="px-6 py-4 text-sm font-bold">{fmtUSD(tx.amount_usd)}</td>
                      <td className="px-6 py-4 font-mono text-xs text-outline">
                        {tx.counterparty ? `${tx.counterparty.slice(0, 8)}...${tx.counterparty.slice(-4)}` : '--'}
                      </td>
                      <td className="px-6 py-4 text-xs text-outline">
                        {tx.tx_time ? new Date(tx.tx_time).toLocaleString() : '--'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-12 text-center text-on-surface-variant">
                <span className="material-symbols-outlined text-4xl mb-3 block opacity-30">receipt_long</span>
                <p className="text-sm">No transaction data yet.</p>
              </div>
            )}
          </section>

          {/* Top Counterparties */}
          {data.top_counterparties?.length > 0 && (
            <section className="bg-surface-container rounded-3xl overflow-hidden">
              <div className="px-6 py-5 border-b border-outline-variant/10">
                <h2 className="font-headline font-bold text-lg">Top Counterparties</h2>
              </div>
              <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-3">
                {data.top_counterparties.map((cp: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-surface-container-low">
                    <span className="font-mono text-xs text-on-surface">
                      {cp.address.slice(0, 10)}...{cp.address.slice(-6)}
                    </span>
                    <span className="text-xs font-bold text-outline">{cp.tx_count} txs</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      {/* Empty State (no search yet) */}
      {!analyzing && !data && !error && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <span className="material-symbols-outlined text-6xl text-outline mb-4 opacity-30" style={{ fontVariationSettings: "'FILL' 1" }}>manage_search</span>
          <p className="text-on-surface-variant text-lg font-headline mb-2">Enter any wallet address</p>
          <p className="text-outline text-sm">Supports ETH, BSC, and Solana addresses.</p>
        </div>
      )}
    </div>
  );
};

export default WalletIntelligence;
