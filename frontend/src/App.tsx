import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { PWAProvider } from './contexts/PWAContext';
import AppRoutes from "./routes/AppRoutes";
import { ErrorBoundary } from './components/shared/ErrorBoundary';
import { OfflineIndicator, PwaDock } from './components/shared';
import { PetProvider } from './pet/PetContext';
import { PetWidget } from './pet/PetWidget';

export const App: React.FC = () => (
  <BrowserRouter>
    <ErrorBoundary>
      <PWAProvider>
        <AuthProvider>
          <PetProvider>
            {/*
              PWA chrome is mounted here rather than inside a layout so it is
              present on the unauthenticated login screen too - that is exactly
              where a first-time user decides to install the app.
            */}
            <OfflineIndicator />
            <AppRoutes />
            <PwaDock />
            <PetWidget />
          </PetProvider>
        </AuthProvider>
      </PWAProvider>
    </ErrorBoundary>
  </BrowserRouter>
);

export default App;
