// src/pages/teacher/Subscription.tsx
import React from 'react';
import { MySubscription } from '../../components/subscriptions/MySubscription';

/**
 * Teacher subscription screen. All data comes from `/subscription/me*`;
 * this page stays reachable even while the gated modules are locked.
 */
export const TeacherSubscription: React.FC = () => <MySubscription />;

export default TeacherSubscription;
