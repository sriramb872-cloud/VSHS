import React, { createContext, useContext, useEffect, useMemo, useState, ReactNode } from 'react';
import { PetDashboardData, PetRole, PetState, getPetState } from './petStateMachine';

interface PetContextValue {
  state: PetState;
  setDashboardData: (role: PetRole, data: PetDashboardData) => void;
  greet: () => void;
  farewell: () => void;
}

const PetContext = createContext<PetContextValue | undefined>(undefined);

export const PetProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [role, setRole] = useState<PetRole>('');
  const [data, setData] = useState<PetDashboardData>({});
  const [transient, setTransient] = useState<{ greeting: boolean; farewell: boolean }>({ greeting: false, farewell: false });

  useEffect(() => {
    const onGreeting = () => { setTransient({ greeting: true, farewell: false }); window.setTimeout(() => setTransient(v => ({ ...v, greeting: false })), 4000); };
    const onFarewell = () => setTransient({ greeting: false, farewell: true });
    window.addEventListener('scholaris:pet-greeting', onGreeting);
    window.addEventListener('scholaris:pet-farewell', onFarewell);
    return () => { window.removeEventListener('scholaris:pet-greeting', onGreeting); window.removeEventListener('scholaris:pet-farewell', onFarewell); };
  }, []);

  const value = useMemo(() => ({
    state: getPetState(role, data, transient),
    setDashboardData: (nextRole: PetRole, nextData: PetDashboardData) => { setRole(nextRole); setData(nextData); },
    greet: () => window.dispatchEvent(new Event('scholaris:pet-greeting')),
    farewell: () => window.dispatchEvent(new Event('scholaris:pet-farewell')),
  }), [role, data, transient]);
  return <PetContext.Provider value={value}>{children}</PetContext.Provider>;
};

export const usePet = (): PetContextValue => {
  const value = useContext(PetContext);
  if (!value) throw new Error('usePet must be used within PetProvider');
  return value;
};
