// src/components/settings/index.tsx
import React, { useState } from 'react';
import { settingsService } from '../../services/settings';

interface UserSettingsSectionProps {
  initialProfile: Record<string, any>;
  initialNotifications: Record<string, any>;
}

export const UserSettingsSection: React.FC<UserSettingsSectionProps> = ({ initialProfile, initialNotifications }) => {
  const [profile, setProfile] = useState(initialProfile);
  const [notifications, setNotifications] = useState(initialNotifications);
  const [passwords, setPasswords] = useState({ current_password: '', new_password: '' });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');
    try {
      await settingsService.updateUserSettings({
        id: 1,
        profile_information: profile,
        notification_preferences: notifications
      });
      setMessage('Settings updated successfully!');
    } catch (err: any) {
      setError('Failed to update settings.');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');
    try {
      await settingsService.changePassword(passwords);
      setMessage('Password changed successfully!');
      setPasswords({ current_password: '', new_password: '' });
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to change password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto py-6">
      {message && <div className="p-4 bg-green-50 border border-green-200 text-green-700 rounded">{message}</div>}
      {error && <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded">{error}</div>}

      <form onSubmit={handleProfileSave} className="bg-white p-6 shadow rounded-lg space-y-4">
        <h2 className="text-xl font-bold text-gray-900">Profile Information</h2>
        <div>
          <label className="block text-sm font-medium text-gray-700">Name</label>
          <input
            type="text"
            value={profile.name || ''}
            onChange={(e) => setProfile({ ...profile, name: e.target.value })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm border p-2"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Email</label>
          <input
            type="email"
            value={profile.email || ''}
            onChange={(e) => setProfile({ ...profile, email: e.target.value })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm border p-2"
          />
        </div>

        <h3 className="text-lg font-medium text-gray-900 pt-4">Notification Preferences</h3>
        <div className="space-y-2">
          {Object.keys(notifications).map((key) => (
            <label key={key} className="flex items-center space-x-3">
              <input
                type="checkbox"
                checked={!!notifications[key]}
                onChange={(e) => setNotifications({ ...notifications, [key]: e.target.checked })}
                className="h-4 w-4 text-indigo-600 border-gray-300 rounded"
              />
              <span className="text-sm font-medium text-gray-700 capitalize">{key} Notifications</span>
            </label>
          ))}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? 'Saving...' : 'Save Changes'}
        </button>
      </form>

      <form onSubmit={handlePasswordChange} className="bg-white p-6 shadow rounded-lg space-y-4">
        <h2 className="text-xl font-bold text-gray-900">Change Password</h2>
        <div>
          <label className="block text-sm font-medium text-gray-700">Current Password</label>
          <input
            type="password"
            value={passwords.current_password}
            onChange={(e) => setPasswords({ ...passwords, current_password: e.target.value })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm border p-2"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">New Password</label>
          <input
            type="password"
            value={passwords.new_password}
            onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm border p-2"
            required
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-gray-800 text-white rounded hover:bg-gray-900 disabled:opacity-50"
        >
          {loading ? 'Updating...' : 'Update Password'}
        </button>
      </form>
    </div>
  );
};