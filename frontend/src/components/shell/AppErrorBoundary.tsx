/**
 * AppErrorBoundary — last line of defense against a blank white screen.
 *
 * TanStack Query's `queryCache`/`mutationCache` `onError` (see
 * `lib/queryClient.ts`) already turns failed *data fetching* into a toast
 * without ever throwing into the render tree, so this boundary should
 * rarely fire in practice. It exists for the remaining class of failure
 * that toasts can't catch: a render-time exception (a bad prop shape from
 * an evolving backend schema, a third-party library throwing during a
 * commit, etc.). React error boundaries can only be class components —
 * there is no hook equivalent.
 *
 * The fallback deliberately does not print `error.stack` or `error.message`
 * to the screen (only to the console, for whoever is at the machine) —
 * investigators are the audience here, not developers, and a raw stack
 * trace is exactly the kind of thing this ticket asks us to stop showing.
 */

import React from 'react';
import { Button, FolderCard, StampBadge } from '../../design-system';

interface AppErrorBoundaryProps {
  children: React.ReactNode;
}

interface AppErrorBoundaryState {
  hasError: boolean;
}

export class AppErrorBoundary extends React.Component<
  AppErrorBoundaryProps,
  AppErrorBoundaryState
> {
  state: AppErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): AppErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: unknown, info: React.ErrorInfo): void {
    // eslint-disable-next-line no-console
    console.error('AppErrorBoundary caught a render error:', error, info.componentStack);
  }

  private handleReload = (): void => {
    this.setState({ hasError: false });
    window.location.assign('/');
  };

  render(): React.ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div className="flex min-h-screen items-center justify-center bg-cream px-4 py-10">
        <div className="w-full max-w-lg">
          <FolderCard
            tabTitle="CONSOLE // FAULT"
            tabPosition="left"
            tabBadge="!"
            classification="UNRECOVERABLE DISPLAY FAULT"
            elevation="raised"
          >
            <div className="flex flex-col items-center gap-4 py-4 text-center">
              <StampBadge label="CONSOLE FAULT" variant="terracotta" rotation={-2} />
              <div>
                <h2 className="type-display-lg text-pine">Something went wrong</h2>
                <p className="type-body mt-2 text-pine/70">
                  This screen hit an unexpected error and couldn&apos;t render. Your case
                  data is untouched — this is a display fault, not a data-loss event.
                  Returning to the console should clear it.
                </p>
              </div>
              <Button variant="primary" onClick={this.handleReload}>
                Return to console
              </Button>
            </div>
          </FolderCard>
        </div>
      </div>
    );
  }
}
