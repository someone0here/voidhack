import React from 'react';

export const App: React.FC = () => {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-6 text-dossier-readout">
      <div className="w-full max-w-xl rounded-lg border border-dossier-border bg-dossier-surface p-8 shadow-2xl backdrop-blur-md">
        <div className="mb-4 flex items-center justify-between border-b border-dossier-border pb-3">
          <span className="font-mono text-xs uppercase tracking-widest text-dossier-amber">
            Field Dossier // System Scaffold
          </span>
          <span className="rounded bg-dossier-border/60 px-2 py-0.5 font-mono text-xs text-dossier-cyan">
            Phase 1
          </span>
        </div>
        <h1 className="text-xl font-bold tracking-tight text-dossier-readout">
          Cyber Fraud Correlator
        </h1>
        <p className="mt-2 text-sm text-dossier-muted">
          Law enforcement multi-source artifact correlation console. Ready for pipeline
          integration.
        </p>
      </div>
    </div>
  );
};

export default App;
