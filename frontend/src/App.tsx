import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Watchlist from './pages/Watchlist';
import AlertsCenter from './pages/AlertsCenter';
import WalletIntelligence from './pages/WalletIntelligence';

const queryClient = new QueryClient();

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/watchlist" element={<Watchlist />} />
            <Route path="/intelligence" element={<WalletIntelligence />} />
            <Route path="/intelligence/:address" element={<WalletIntelligence />} />
            <Route path="/alerts" element={<AlertsCenter />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  );
};

export default App;
