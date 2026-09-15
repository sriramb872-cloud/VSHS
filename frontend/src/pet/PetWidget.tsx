import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { idleActivities } from './petIdleActivities';
import { farewellGreeting, timeOfDayGreeting } from './petGreetings';
import { usePet } from './PetContext';

export const PetWidget: React.FC = () => {
  const { user } = useAuth();
  const { state } = usePet();
  const [activity, setActivity] = useState(0);
  useEffect(() => { const timer = window.setInterval(() => setActivity(Math.floor(Math.random() * idleActivities.length)), 12000); return () => window.clearInterval(timer); }, []);
  if (!user) return null;
  const idle = idleActivities[activity];
  const content = state === 'greeting' ? { emoji: '🙏', text: timeOfDayGreeting() } : state === 'farewell' ? { emoji: '👋', text: farewellGreeting } : state === 'notify' ? { emoji: '🔔', text: 'You have a new announcement' } : state === 'worried' ? { emoji: '😟', text: 'Let’s catch up on this together...' } : state === 'happy' ? { emoji: '🌟', text: 'Wonderful progress!' } : idle;
  return <div className="fixed bottom-20 right-4 sm:bottom-5 z-[60] flex items-end gap-2 pointer-events-none" aria-live="polite"><div className="rounded-2xl bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 shadow-lg border border-slate-200 max-w-[190px]">{content.text}</div><div className="h-12 w-12 rounded-full bg-gradient-to-br from-amber-300 to-orange-500 shadow-lg border-2 border-white flex items-center justify-center text-2xl" title="SCHOLARIS companion">{content.emoji}</div></div>;
};
