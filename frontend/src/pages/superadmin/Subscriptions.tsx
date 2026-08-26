// src/pages/superadmin/Subscriptions.tsx
import React, { useState, useEffect } from 'react';
import { CreditCard } from 'lucide-react';
import { MobileListItem, EmptyState, LoadingSkeleton, StatusBadge } from '../../components/shared';

export const SuperAdminSubscriptions: React.FC = () => {
  const [subscriptions, setSubscriptions] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch subscription data
    setLoading(false);
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Subscriptions</h1>
        <p className="text-xs text-slate-500">School licensing and billing status</p>
      </div>

      {error && <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>}

      {loading ? (
        <LoadingSkeleton type="list" count={4} />
      ) : subscriptions.length === 0 ? (
        <EmptyState
          title="No Subscription Records"
          description="No active subscription records found for onboarded schools."
          icon={<CreditCard className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {subscriptions.map((sub, idx) => (
            <MobileListItem
              key={idx}
              title={sub.school_name || 'School Subscription'}
              subtitle={`Plan: ${sub.plan || 'Enterprise Tier'}`}
              icon={<CreditCard className="w-5 h-5 text-indigo-600" />}
              avatarBg="bg-indigo-50 text-indigo-600"
              badge={<StatusBadge status={sub.status || 'ACTIVE'} />}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default SuperAdminSubscriptions;