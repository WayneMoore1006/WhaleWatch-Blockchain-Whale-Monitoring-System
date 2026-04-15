import React from 'react';

export const SummaryCard: React.FC<{
  title: string;
  value: string;
  change?: string;
  icon: string;
  isTertiary?: boolean;
  isHighlight?: boolean;
}> = ({ title, value, change, icon, isTertiary, isHighlight }) => {
  return (
    <div className={`p-6 rounded-2xl relative overflow-hidden group border border-outline-variant/5 shadow-sm ${
      isHighlight ? 'bg-surface-container shadow-xl' : 'bg-surface-container-low'
    }`}>
      {isHighlight && (
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent"></div>
      )}
      <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
        <span className="material-symbols-outlined text-6xl">{icon}</span>
      </div>
      <p className={`text-xs font-bold uppercase tracking-widest mb-2 relative z-10 ${
        isHighlight ? 'text-primary' : 'text-outline'
      }`}>
        {title}
      </p>
      <div className="flex items-end gap-2 relative z-10">
        <span className="text-3xl font-headline font-bold text-on-surface">{value}</span>
        {change && (
          <span className={`${isTertiary ? 'text-tertiary' : 'text-secondary'} text-xs font-bold mb-1`}>
            {change}
          </span>
        )}
        {isHighlight && (
           <span className="px-2 py-0.5 rounded-full bg-secondary-container/20 text-secondary text-[10px] font-bold mb-1 uppercase tracking-tighter">
             High Risk
           </span>
        )}
      </div>
    </div>
  );
};

export const ChainBadge: React.FC<{ chain: string; isActive?: boolean; onClick?: () => void }> = ({ chain, isActive, onClick }) => {
  return (
    <button 
      onClick={onClick}
      className={`px-4 py-1.5 text-xs font-bold rounded-lg transition-all ${
        isActive 
          ? 'bg-[#adc6ff]/10 text-[#adc6ff]' 
          : 'text-slate-500 hover:text-slate-300'
      }`}
    >
      {chain}
    </button>
  );
};

export const StatusBadge: React.FC<{ type: 'success' | 'warning' | 'danger' | 'neutral'; label: string }> = ({ type, label }) => {
  const styles = {
    success: 'bg-secondary-container/20 text-secondary',
    warning: 'bg-primary-container/20 text-primary',
    danger: 'bg-tertiary-container/20 text-tertiary',
    neutral: 'bg-surface-container-highest text-outline',
  };

  return (
    <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-tighter ${styles[type]}`}>
      {label}
    </span>
  );
};
