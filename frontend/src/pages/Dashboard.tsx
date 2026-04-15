import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import { ChainBadge } from '../components/Common';
import { CardSkeleton, ChartSkeleton, TableSkeleton } from '../components/Skeleton';

const API = 'http://localhost:8000';
const CHAINS = ['ETH', 'BSC', 'SOL'];

const formatUSD = (v: number | null | undefined) =>
  v != null ? `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '--';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [activeChain, setActiveChain] = useState('ETH');
  const [overview, setOverview] = useState<any>(null);
  const [topWallets, setTopWallets] = useState<any[]>([]);
  const [recentTransfers, setRecentTransfers] = useState<any[]>([]);
  const [trend, setTrend] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  // 分鏈快取，避免切換時白屏
  const cache = React.useRef<Record<string, any>>({});

  const fetchData = useCallback(async (chain: string) => {
    setLoading(true);
    setError(null);

    // 如果快取有資料，先填入以立即顯示
    if (cache.current[chain]) {
      const c = cache.current[chain];
      setOverview(c.overview);
      setTopWallets(c.topWallets);
      setRecentTransfers(c.recentTransfers);
      setTrend(c.trend);
    }

    try {
      const [ovRes, topRes, txRes, trendRes] = await Promise.all([
        fetch(`${API}/api/dashboard/overview?chain=${chain}`),
        fetch(`${API}/api/dashboard/top-wallets?chain=${chain}&limit=10`),
        fetch(`${API}/api/dashboard/recent-transfers?chain=${chain}&limit=10`),
        fetch(`${API}/api/dashboard/tx-volume-trend?chain=${chain}&days=7`)
      ]);
      const [ov, top, tx, trendData] = await Promise.all([
        ovRes.json(), topRes.json(), txRes.json(), trendRes.json()
      ]);
      
      const newData = {
        overview: ov,
        topWallets: Array.isArray(top) ? top : [],
        recentTransfers: Array.isArray(tx) ? tx : [],
        trend: trendData.trend || []
      };

      // 更新狀態 & 快取
      setOverview(newData.overview);
      setTopWallets(newData.topWallets);
      setRecentTransfers(newData.recentTransfers);
      setTrend(newData.trend);
      cache.current[chain] = newData;
      
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (e: any) {
      setError('Failed to connect to API. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(activeChain); }, [activeChain, fetchData]);

  // 只有在完全沒有資料且正在載入時才顯示全螢幕骨架
  const showSkeleton = loading && !overview;

  if (showSkeleton) return (
    <div className="animate-in fade-in duration-500">
      <div className="flex justify-between items-end mb-8">
        <div className="h-10 w-64 bg-surface-container-highest rounded-lg animate-pulse" />
        <div className="h-10 w-48 bg-surface-container-highest rounded-lg animate-pulse" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <CardSkeleton /><CardSkeleton /><CardSkeleton /><CardSkeleton />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
        <div className="lg:col-span-8"><ChartSkeleton /></div>
        <div className="lg:col-span-4"><ChartSkeleton /></div>
      </div>
      <TableSkeleton />
    </div>
  );

  const hasData = !overview?.error && overview?.tracked_wallets != null;

  return (
    <div className="animate-in fade-in duration-500">
      {/* Header & Chain Tabs */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
          <h1 className="text-3xl font-headline font-bold tracking-tight text-on-surface">Intelligence Dashboard</h1>
          <p className="text-on-surface-variant text-sm mt-1">
            Real-time on-chain monitoring — ETH / BSC / SOL
            {lastUpdated && <span className="ml-2 opacity-50">· Updated {lastUpdated}</span>}
          </p>
        </div>
        <div className="flex bg-surface-container-low p-1 rounded-xl gap-1">
          {CHAINS.map(chain => (
            <ChainBadge
              key={chain} chain={chain}
              isActive={activeChain === chain}
              onClick={() => setActiveChain(chain)}
            />
          ))}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mb-6 p-4 rounded-xl bg-tertiary-container/20 border border-tertiary/30 text-tertiary text-sm flex items-center gap-2">
          <span className="material-symbols-outlined">warning</span>{error}
        </div>
      )}

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard title="Tracked Wallets" value={hasData ? String(overview.tracked_wallets) : '--'}
          icon="account_balance_wallet" pending={!hasData} />
        <StatCard title="24h Transactions" value={hasData ? String(overview.tx_24h) : '--'}
          icon="swap_horiz" pending={!hasData} />
        <StatCard title="Net Flow (Today)"
          value={hasData && overview.netflow_usd != null ? formatUSD(overview.netflow_usd) : '--'}
          icon="trending_up" pending={!hasData} isTertiary />
        <StatCard title="Active Alerts" value={hasData ? String(overview.active_alerts) : '--'}
          icon="notifications_active" pending={!hasData} isHighlight />
      </div>

      {/* TX Volume Trend Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
        <div className="lg:col-span-8 bg-surface-container-low p-6 rounded-2xl border border-outline-variant/5">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-headline font-bold text-lg">Daily TX Volume Trend (7d)</h3>
            <span className="text-[10px] font-bold uppercase tracking-widest text-outline">Source: DB</span>
          </div>
          {trend.length > 0 ? (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trend}>
                  <defs>
                    <linearGradient id="colorTx" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#adc6ff" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#adc6ff" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#424754" vertical={false} opacity={0.2} />
                  <XAxis dataKey="date" stroke="#8c909f" fontSize={10} tickLine={false} axisLine={false} dy={10} />
                  <YAxis hide />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1f2022', border: '1px solid #424754', borderRadius: '8px', fontSize: '12px' }}
                    formatter={(v: any, name: any) => [Number(v).toLocaleString(), name === 'tx_count' ? 'Transactions' : String(name)]}
                  />
                  <Area type="monotone" dataKey="tx_count" stroke="#adc6ff" strokeWidth={2}
                    fillOpacity={1} fill="url(#colorTx)" name="tx_count" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyChart message="Data sync pending — no daily stats yet" />
          )}
        </div>

        {/* Net Flow Summary */}
        <div className="lg:col-span-4 bg-surface-container-low p-6 rounded-2xl border border-outline-variant/5 flex flex-col gap-4">
          <h3 className="font-headline font-bold text-lg">Flow Summary (Today)</h3>
          {hasData ? (
            <div className="flex flex-col gap-3 mt-2">
              <FlowRow label="Total Inflow" value={formatUSD(overview.inflow_usd)} color="text-secondary" />
              <FlowRow label="Total Outflow" value={formatUSD(overview.outflow_usd)} color="text-tertiary" />
              <div className="border-t border-outline-variant/20 pt-3">
                <FlowRow label="Net Flow" value={formatUSD(overview.netflow_usd)}
                  color={overview.netflow_usd >= 0 ? 'text-secondary' : 'text-tertiary'} bold />
              </div>
              <p className="text-[10px] text-outline uppercase tracking-wider mt-2">Chain: {activeChain}</p>
            </div>
          ) : (
            <p className="text-sm text-on-surface-variant mt-4">No flow data yet. Add wallets to the watchlist to start tracking.</p>
          )}
        </div>
      </div>

      {/* Recent Large Transfers */}
      {recentTransfers.length > 0 && (
        <div className="bg-surface-container-low rounded-2xl overflow-hidden border border-outline-variant/5 mb-8">
          <div className="p-6 border-b border-outline-variant/10">
            <h3 className="font-headline font-bold text-lg">Recent Large Transfers</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="text-[10px] uppercase tracking-widest text-outline border-b border-outline-variant/5 font-bold">
                  <th className="px-6 py-4">Direction</th>
                  <th className="px-6 py-4">Asset</th>
                  <th className="px-6 py-4">Amount (USD)</th>
                  <th className="px-6 py-4">Counterparty</th>
                  <th className="px-6 py-4">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/5">
                {recentTransfers.map((tx, i) => (
                  <tr key={i} className="hover:bg-surface-container-high/30 transition-colors">
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase ${tx.direction === 'in' ? 'bg-secondary/20 text-secondary' : 'bg-tertiary/20 text-tertiary'}`}>
                        {tx.direction === 'in' ? '↓ IN' : '↑ OUT'}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-sm">{tx.asset_symbol}</td>
                    <td className="px-6 py-4 font-bold">{formatUSD(tx.amount_usd)}</td>
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
          </div>
        </div>
      )}

      {/* Top Active Wallets */}
      <div className="bg-surface-container-low rounded-2xl overflow-hidden border border-outline-variant/5">
        <div className="p-6 border-b border-outline-variant/10 flex items-center justify-between">
          <h3 className="font-headline font-bold text-lg">Top Active Wallets (24h)</h3>
          <button onClick={() => navigate('/watchlist')}
            className="text-[10px] font-bold text-primary flex items-center gap-1 hover:opacity-80 uppercase tracking-widest">
            VIEW WATCHLIST <span className="material-symbols-outlined text-sm">chevron_right</span>
          </button>
        </div>
        {topWallets.length === 0 ? (
          <div className="p-12 text-center">
            <span className="material-symbols-outlined text-4xl text-outline mb-4 block">inbox</span>
            <p className="text-on-surface-variant text-sm">No wallet data yet.</p>
            <p className="text-outline text-xs mt-1">Add wallets to the watchlist and wait for sync.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="text-[10px] uppercase tracking-widest text-outline border-b border-outline-variant/5 font-bold">
                  <th className="px-6 py-4">Wallet</th>
                  <th className="px-6 py-4">Chain</th>
                  <th className="px-6 py-4">24h Txs</th>
                  <th className="px-6 py-4">24h Volume</th>
                  <th className="px-6 py-4">Balance (USD)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/5">
                {topWallets.map((w, i) => (
                  <tr key={i} onClick={() => navigate(`/intelligence/${w.address}`)}
                    className="hover:bg-surface-container-high/30 transition-colors cursor-pointer">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-xl bg-surface-container-highest flex items-center justify-center font-mono text-primary font-bold text-xs">
                          {(w.label || 'WH').substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <p className="text-sm font-bold text-on-surface">{w.label || 'Whale'}</p>
                          <p className="text-[10px] font-mono text-outline">{w.address.slice(0, 8)}...{w.address.slice(-4)}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 rounded bg-surface-container text-[10px] font-bold text-outline uppercase">{w.chain}</span>
                    </td>
                    <td className="px-6 py-4 font-bold">{w.tx_count_24h}</td>
                    <td className="px-6 py-4">{formatUSD(w.volume_usd_24h)}</td>
                    <td className="px-6 py-4">{formatUSD(w.native_balance_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

// ── Internal sub-components ────────────────────────────────────
const StatCard = ({ title, value, icon, pending, isTertiary, isHighlight }: any) => (
  <div className={`p-6 rounded-2xl border ${isHighlight ? 'bg-tertiary-container/10 border-tertiary/20' : 'bg-surface-container-low border-outline-variant/5'}`}>
    <div className="flex items-center justify-between mb-4">
      <span className={`text-[10px] font-bold uppercase tracking-widest ${isHighlight ? 'text-tertiary' : 'text-outline'}`}>{title}</span>
      <span className={`material-symbols-outlined text-lg ${isHighlight ? 'text-tertiary' : isTertiary ? 'text-secondary' : 'text-primary'}`} style={{ fontVariationSettings: "'FILL' 1" }}>{icon}</span>
    </div>
    <p className={`text-2xl font-headline font-bold ${pending ? 'text-outline text-base' : isHighlight ? 'text-tertiary' : 'text-on-surface'}`}>
      {pending ? 'Data sync pending' : value}
    </p>
  </div>
);

const FlowRow = ({ label, value, color, bold }: any) => (
  <div className="flex items-center justify-between">
    <span className="text-xs text-on-surface-variant">{label}</span>
    <span className={`text-sm font-mono ${bold ? `font-bold ${color}` : color}`}>{value}</span>
  </div>
);

const EmptyChart = ({ message }: { message: string }) => (
  <div className="h-64 flex flex-col items-center justify-center text-on-surface-variant">
    <span className="material-symbols-outlined text-4xl mb-3 opacity-30">bar_chart</span>
    <p className="text-sm opacity-60">{message}</p>
  </div>
);

export default Dashboard;
