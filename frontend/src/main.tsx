import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import { queryClient } from './lib/queryClient';
import { AppErrorBoundary } from './components/shell/AppErrorBoundary';
import { AppToaster } from './design-system';
import './index.css';

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Root element not found in document');
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <App />
        <AppToaster />
      </QueryClientProvider>
    </AppErrorBoundary>
  </React.StrictMode>,
);
