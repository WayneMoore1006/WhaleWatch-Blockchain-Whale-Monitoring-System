import React from 'react';

export const CardSkeleton: React.FC = () => (
  <div className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/10 animate-pulse">
    <div className="h-4 w-24 bg-surface-container-highest rounded mb-4"></div>
    <div className="h-8 w-32 bg-surface-container-highest rounded mb-2"></div>
    <div className="h-4 w-16 bg-surface-container-highest rounded"></div>
  </div>
);

export const ChartSkeleton: React.FC = () => (
  <div className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/10 animate-pulse h-64 flex flex-col justify-end gap-2">
    <div className="h-4 w-48 bg-surface-container-highest rounded mb-auto"></div>
    <div className="flex items-end gap-2 h-32">
      {[40, 70, 45, 90, 65, 80, 50].map((h, i) => (
        <div key={i} className="flex-1 bg-surface-container-highest rounded-t" style={{ height: `${h}%` }}></div>
      ))}
    </div>
    <div className="h-2 w-full bg-surface-container-highest rounded mt-4"></div>
  </div>
);

export const TableSkeleton: React.FC = () => (
  <div className="bg-surface-container-low rounded-2xl overflow-hidden border border-outline-variant/10 animate-pulse">
    <div className="p-6 border-b border-outline-variant/10 flex justify-between">
      <div className="h-6 w-48 bg-surface-container-highest rounded"></div>
      <div className="h-6 w-24 bg-surface-container-highest rounded"></div>
    </div>
    <div className="p-6 space-y-4">
      {[1, 2, 3, 4].map(i => (
        <div key={i} className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-surface-container-highest"></div>
          <div className="flex-1 space-y-2">
            <div className="h-4 w-1/3 bg-surface-container-highest rounded"></div>
            <div className="h-3 w-1/4 bg-surface-container-highest rounded"></div>
          </div>
          <div className="h-4 w-24 bg-surface-container-highest rounded"></div>
          <div className="h-4 w-16 bg-surface-container-highest rounded"></div>
        </div>
      ))}
    </div>
  </div>
);

export const WalletDetailSkeleton: React.FC = () => (
  <div className="animate-pulse space-y-8">
    <div className="flex justify-between items-end">
      <div className="space-y-4">
        <div className="h-4 w-32 bg-surface-container-highest rounded"></div>
        <div className="h-10 w-96 bg-surface-container-highest rounded"></div>
      </div>
      <div className="h-10 w-32 bg-surface-container-highest rounded"></div>
    </div>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <CardSkeleton />
      <CardSkeleton />
      <CardSkeleton />
    </div>
    <div className="h-64 bg-surface-container-low rounded-3xl border border-outline-variant/10"></div>
  </div>
);
