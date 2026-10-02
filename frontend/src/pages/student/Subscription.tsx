// src/pages/student/Subscription.tsx
import React from 'react';
import { MySubscription } from '../../components/subscriptions/MySubscription';

/**
 * Student subscription screen. All data comes from `/subscription/me*`;
 * this page stays reachable even while the gated modules are locked.
 */
export const StudentSubscription: React.FC = () => <MySubscription />;

export default StudentSubscription;
