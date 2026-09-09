import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import AppRoutes from "./routes/AppRoutes";
import { ErrorBoundary } from './components/shared/ErrorBoundary';

export const App: React.FC = () => (
  <BrowserRouter>
    <ErrorBoundary>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ErrorBoundary>
  </BrowserRouter>
);

export default App;