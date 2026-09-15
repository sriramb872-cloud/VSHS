import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import AppRoutes from "./routes/AppRoutes";
import { ErrorBoundary } from './components/shared/ErrorBoundary';
import { PetProvider } from './pet/PetContext';
import { PetWidget } from './pet/PetWidget';

export const App: React.FC = () => (
  <BrowserRouter>
    <ErrorBoundary>
      <AuthProvider>
        <PetProvider>
          <AppRoutes />
          <PetWidget />
        </PetProvider>
      </AuthProvider>
    </ErrorBoundary>
  </BrowserRouter>
);

export default App;
