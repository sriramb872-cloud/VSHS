// src/pages/principal/Subscription.tsx
import React from 'react';
import { MySubscription } from '../../components/subscriptions/MySubscription';

/**
 * Principal subscription screen. All data comes from `/subscription/me*`;
 * this page stays reachable even while the gated modules are locked.
 */
export const PrincipalSubscription: React.FC = () => <MySubscription />;

export default PrincipalSubscription;
