import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { AcademicYearProvider } from './contexts/AcademicYearContext';
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
          {/*
            AcademicYearProvider sits *inside* AuthProvider so it can wait for a
            signed-in user before requesting the school's years (requesting them
            while logged out would only produce a 401 and a redirect loop), and
            *outside* every layout so all four role shells share one selection.
          */}
          <AcademicYearProvider>
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
          </AcademicYearProvider>
        </AuthProvider>
      </PWAProvider>
    </ErrorBoundary>
  </BrowserRouter>
);

export default App;
