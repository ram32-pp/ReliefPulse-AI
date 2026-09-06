'use client';

import React from 'react';

export const StatsBar: React.FC = () => {
  return (
    <div className="flex items-center gap-6 overflow-x-auto whitespace-nowrap">
      <div className="flex items-center gap-2">
        <div className="w-3 h-3 rounded-full bg-pulse-red animate-pulse"></div>
        <span className="text-sm font-medium text-slate-600">Critical: <span className="text-pulse-red font-bold text-base">12</span></span>
      </div>
      <div className="w-px h-6 bg-slate-200"></div>
      
      <div className="flex items-center gap-2">
        <div className="w-3 h-3 rounded-full bg-amber-alert"></div>
        <span className="text-sm font-medium text-slate-600">High: <span className="text-amber-alert font-bold text-base">34</span></span>
      </div>
      <div className="w-px h-6 bg-slate-200"></div>
      
      <div className="flex items-center gap-2">
        <div className="w-3 h-3 rounded-full bg-relief-green"></div>
        <span className="text-sm font-medium text-slate-600">Resolved: <span className="text-relief-green font-bold text-base">156</span></span>
      </div>
      <div className="w-px h-6 bg-slate-200"></div>
      
      <div className="flex items-center gap-2">
        <span className="text-xl">📊</span>
        <span className="text-sm font-medium text-slate-600">Clusters: <span className="text-deep-navy font-bold text-base">8</span></span>
      </div>
      <div className="w-px h-6 bg-slate-200"></div>

      <div className="flex items-center gap-2">
        <span className="text-xl">⏱️</span>
        <span className="text-sm font-medium text-slate-600">Avg Response: <span className="text-deep-navy font-bold text-base">23min</span></span>
      </div>
    </div>
  );
};
