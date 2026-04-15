import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const location = useLocation();

  const navItems = [
    { title: 'Dashboard', path: '/', icon: 'dashboard' },
    { title: 'Watchlist', path: '/watchlist', icon: 'visibility' },
    { title: 'Wallet Intelligence', path: '/intelligence', icon: 'query_stats' },
    { title: 'Alerts Center', path: '/alerts', icon: 'notifications_active' },
  ];

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden" 
          onClick={onClose}
        />
      )}

      <aside className={`fixed left-0 top-0 h-full z-40 flex flex-col w-64 border-r-0 bg-[#1b1c1e] transition-transform duration-300 transform ${isOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0`}>
        <div className="px-6 py-8">
          <span className="text-xl font-bold tracking-tighter text-[#adc6ff] font-headline">WhaleWatch</span>
        </div>
        
        <nav className="flex-1 px-4 space-y-2 font-headline text-sm tracking-tight">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={`flex items-center gap-3 px-4 py-3 transition-all duration-200 rounded-lg ${
                  isActive 
                    ? 'text-[#adc6ff] font-bold border-r-2 border-[#adc6ff] bg-gradient-to-r from-[#adc6ff]/10 to-transparent scale-98' 
                    : 'text-slate-500 hover:text-slate-300 hover:bg-[#1f2022]'
                }`}
              >
                <span className="material-symbols-outlined">{item.icon}</span>
                {item.title}
              </Link>
            );
          })}
        </nav>

        <div className="p-6 mt-auto">
          <div className="p-4 rounded-xl bg-surface-container-high/50 border border-outline-variant/10">
            <p className="text-[10px] uppercase tracking-widest text-outline mb-2">Pro Plan</p>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold">Infinite Scan</span>
              <span className="text-xs text-secondary">Active</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

const API = 'http://localhost:8000';
const SEVERITY_COLORS: Record<string, string> = {
  high:   'bg-tertiary/20 text-tertiary',
  medium: 'bg-yellow-500/20 text-yellow-400',
  low:    'bg-primary-container/20 text-primary'
};
const SEVERITY_ICON: Record<string, string> = {
  high: 'warning', medium: 'info', low: 'notifications'
};

const Header: React.FC<{ onMenuClick: () => void }> = ({ onMenuClick }) => {
  const navigate = useNavigate();
  const [alerts, setAlerts] = React.useState<any[]>([]);
  const [showPopover, setShowPopover] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  
  let hoverTimeoutRef = React.useRef<NodeJS.Timeout | null>(null);

  const fetchAlerts = React.useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/alerts?limit=50`);
      if (res.ok) {
        const data = await res.json();
        setAlerts(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.error('Failed to fetch header alerts', e);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 60000); // 60s — 減少後端輪詢壓力
    const handleEvent = () => fetchAlerts();
    window.addEventListener('alertsUpdated', handleEvent);
    return () => {
      clearInterval(interval);
      window.removeEventListener('alertsUpdated', handleEvent);
    };
  }, [fetchAlerts]);

  const handleMouseEnter = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    setShowPopover(true);
  };

  const handleMouseLeave = () => {
    hoverTimeoutRef.current = setTimeout(() => setShowPopover(false), 200);
  };

  const unreadCount = alerts.filter(a => a.status === 'new').length;
  const criticalCount = alerts.filter(a => a.status === 'new' && a.severity === 'high').length;
  const topAlerts = alerts.slice(0, 5);

  const handleSearchKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && e.currentTarget.value.trim()) {
      navigate(`/intelligence/${e.currentTarget.value.trim()}`);
      e.currentTarget.value = ''; // Optional: clear input after search
    }
  };

  return (
    <header className="fixed top-0 right-0 left-0 md:left-64 z-30 flex justify-between items-center px-6 h-16 bg-[#121315]/80 backdrop-blur-xl border-b border-[#424754]/20">
      <div className="flex items-center flex-1 max-w-xl">
        <button onClick={onMenuClick} className="md:hidden mr-4 text-slate-400">
          <span className="material-symbols-outlined">menu</span>
        </button>
        <div className="relative w-full group">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 material-symbols-outlined text-slate-400 group-focus-within:text-[#adc6ff]">search</span>
          <input 
            className="w-full bg-surface-container-high/40 border-0 rounded-lg pl-10 pr-4 py-2 text-sm focus:ring-1 ring-[#adc6ff]/50 transition-all font-headline font-medium outline-none text-[#adc6ff] placeholder-slate-500" 
            placeholder="Search Wallet / Hash (Press Enter)" 
            type="text"
            onKeyDown={handleSearchKeyPress}
          />
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <div 
          className="relative flex items-center justify-center p-2"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <Link to="/alerts" className="text-slate-400 hover:text-white transition-colors relative flex items-center justify-center">
            <span className="material-symbols-outlined">notifications</span>
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-tertiary text-white text-[9px] font-bold h-4 min-w-[16px] px-1 rounded-full flex items-center justify-center border-2 border-[#121315]">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </Link>

          {showPopover && (
            <div className="absolute top-12 right-0 w-80 md:w-96 bg-surface-container-low rounded-xl shadow-2xl border border-outline-variant/20 overflow-hidden z-50">
              <div className="bg-surface-container p-4 border-b border-outline-variant/10 text-sm flex justify-between items-center">
                <div>
                  <span className="font-bold text-on-surface">Notifications</span>
                  {unreadCount > 0 && <span className="ml-2 text-[10px] bg-tertiary/20 text-tertiary px-1.5 py-0.5 rounded-md font-bold">{unreadCount} New</span>}
                </div>
                {criticalCount > 0 && (
                  <span className="text-[10px] text-tertiary flex items-center gap-1 font-bold">
                    <span className="material-symbols-outlined text-[12px]">warning</span>
                    {criticalCount} Critical
                  </span>
                )}
              </div>
              
              <div className="max-h-96 overflow-y-auto">
                {loading && <div className="p-4 text-center text-xs text-outline">Loading...</div>}
                {!loading && topAlerts.length === 0 && (
                  <div className="p-8 text-center text-on-surface-variant flex flex-col items-center">
                    <span className="material-symbols-outlined text-3xl mb-2 opacity-50">notifications_off</span>
                    <span className="text-xs">No alerts found</span>
                  </div>
                )}
                {!loading && topAlerts.map(alert => (
                  <Link key={alert.id} to="/alerts" className={`block p-4 border-b border-outline-variant/5 hover:bg-surface-container transition-colors ${alert.status === 'new' ? 'bg-surface-container-high/30' : 'opacity-70'}`}>
                    <div className="flex gap-3">
                      <div className={`mt-0.5 flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${SEVERITY_COLORS[alert.severity || 'low']}`}>
                        <span className="material-symbols-outlined text-[16px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                          {SEVERITY_ICON[alert.severity || 'low']}
                        </span>
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex justify-between items-start mb-1">
                          <span className={`text-[13px] font-bold truncate ${alert.status === 'new' ? 'text-on-surface' : 'text-on-surface-variant'}`}>
                            {alert.title || alert.alert_type}
                          </span>
                          {alert.status === 'new' && <span className="w-2 h-2 rounded-full bg-secondary flex-shrink-0 mt-1 ml-2"></span>}
                        </div>
                        <div className="text-[11px] text-outline mb-1 flex items-center gap-1">
                          {alert.chain && <span className="uppercase font-bold">{alert.chain}</span>}
                          {alert.chain && <span className="opacity-30">•</span>}
                          <span>{alert.created_at ? new Date(alert.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : ''}</span>
                        </div>
                        {alert.wallet_address && (
                          <div className="text-[10px] font-mono text-outline/70">
                            {alert.wallet_address.slice(0,6)}...{alert.wallet_address.slice(-4)}
                          </div>
                        )}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
              
              <Link to="/alerts" className="block w-full p-3 bg-surface-container-low hover:bg-surface-container text-center text-xs font-bold text-primary transition-colors border-t border-outline-variant/10">
                View all alerts
              </Link>
            </div>
          )}
        </div>
        
        <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-primary to-secondary p-[1px]">
          <div className="h-full w-full rounded-full bg-surface-container overflow-hidden flex items-center justify-center text-[10px] font-bold">
            JD
          </div>
        </div>
      </div>
    </header>
  );
};

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [isSidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen">
      <Sidebar isOpen={isSidebarOpen} onClose={() => setSidebarOpen(false)} />
      <Header onMenuClick={() => setSidebarOpen(true)} />
      
      <main className="pt-24 pb-24 md:pb-8 md:pl-72 pr-6 min-h-screen max-w-[1600px] mx-auto">
        {children}
      </main>

      {/* Mobile Bottom Nav */}
      <nav className="fixed bottom-0 left-0 w-full z-50 flex justify-around items-center px-4 pb-safe h-16 md:hidden bg-[#1b1c1e] border-t border-[#424754]/20 shadow-[0_-10px_30px_rgba(0,0,0,0.5)]">
        <Link to="/" className="flex flex-col items-center justify-center text-slate-500">
          <span className="material-symbols-outlined">home</span>
          <span className="text-[10px] uppercase tracking-widest mt-0.5">Home</span>
        </Link>
        <Link to="/watchlist" className="flex flex-col items-center justify-center text-slate-500">
          <span className="material-symbols-outlined">visibility</span>
          <span className="text-[10px] uppercase tracking-widest mt-0.5">Watch</span>
        </Link>
        <Link to="/intelligence" className="flex flex-col items-center justify-center text-slate-500">
          <span className="material-symbols-outlined">insights</span>
          <span className="text-[10px] uppercase tracking-widest mt-0.5">Intel</span>
        </Link>
        <Link to="/alerts" className="flex flex-col items-center justify-center text-slate-500">
          <span className="material-symbols-outlined">notifications</span>
          <span className="text-[10px] uppercase tracking-widest mt-0.5">Alerts</span>
        </Link>
      </nav>
    </div>
  );
};

export default Layout;
