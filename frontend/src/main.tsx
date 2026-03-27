import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WagmiProvider } from 'wagmi';

import { App } from './App';
import { RuntimeErrorPanel } from './components/RuntimeErrorPanel';
import { createFrontendWagmiConfig, readFrontendEnvironment } from './lib/wagmiConfig';
import './styles/app.css';

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);

try {
  const environment = readFrontendEnvironment();
  const wagmiConfig = createFrontendWagmiConfig(environment);
  const queryClient = new QueryClient();

  root.render(
    <React.StrictMode>
      <WagmiProvider config={wagmiConfig}>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </QueryClientProvider>
      </WagmiProvider>
    </React.StrictMode>,
  );
} catch (error) {
  root.render(
    <React.StrictMode>
      <main className="page-frame">
        <RuntimeErrorPanel
          title="Frontend Environment Error"
          error={error instanceof Error ? error.message : 'Unknown frontend environment error.'}
        />
      </main>
    </React.StrictMode>,
  );
}
