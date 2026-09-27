// src/components/shared/ProfilePhotoUpload.tsx
import React, { useRef, useState } from 'react';
import { Camera, Loader2, Trash2 } from 'lucide-react';
import { filesService } from '../../services/files';
import { useAuth } from '../../contexts/AuthContext';
import UserAvatar from './UserAvatar';
import errorMessage from '../../helpers/errorMessage';

const MAX_BYTES = 5 * 1024 * 1024;
const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp'];

/**
 * Profile-photo uploader.
 *
 * `POST /files/profile-photo` has always existed and worked (server-side), but
 * no screen offered a file input, so the feature was unreachable. Client-side
 * checks mirror the server's so the user gets an immediate reason; the server
 * remains the authority and re-validates the bytes.
 */
export const ProfilePhotoUpload: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const onPick = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    // Allow re-picking the same file after a failure.
    e.target.value = '';
    if (!file) return;

    setError(null);
    setMessage(null);

    if (!ACCEPTED.includes(file.type)) {
      setError('Choose a JPG, PNG or WebP image.');
      return;
    }
    if (file.size > MAX_BYTES) {
      setError('Image must be 5 MB or smaller.');
      return;
    }

    setBusy(true);
    try {
      const res = await filesService.uploadProfilePhoto(file);
      // Re-read the user so the header and sidebar pick up the new photo.
      await refreshUser();
      setMessage(res.message || 'Profile photo updated.');
    } catch (err) {
      setError(errorMessage(err, 'Could not upload the photo. Please try again.'));
    } finally {
      setBusy(false);
    }
  };

  const onRemove = async () => {
    setError(null);
    setMessage(null);
    setBusy(true);
    try {
      // Clears `users.profile_photo`. The stored file and its `uploads` row are
      // kept on the server for audit; only the pointer is dropped.
      const res = await filesService.deleteProfilePhoto();
      await refreshUser();
      setMessage(res.message);
    } catch (err) {
      setError(errorMessage(err, 'Could not remove the photo.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex items-center gap-4">
      <div className="relative">
        <UserAvatar
          src={user?.profile_photo}
          name={user?.display_name}
          className="w-20 h-20"
          rounded="rounded-2xl"
          textClassName="text-xl"
        />
        {busy && (
          <div className="absolute inset-0 rounded-2xl bg-white/70 flex items-center justify-center">
            <Loader2 className="w-5 h-5 text-slate-600 animate-spin" />
          </div>
        )}
      </div>

      <div className="min-w-0">
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={onPick}
          // `sr-only` rather than `hidden`: the field stays reachable by keyboard
          // and screen readers, and the visible button is a convenience.
          className="sr-only"
          aria-label="Profile photo file"
        />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => inputRef.current?.click()}
            className="flex items-center gap-1.5 h-9 px-3 rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-slate-800 active:scale-95 transition-all disabled:opacity-60"
          >
            <Camera className="w-4 h-4" />
            {user?.profile_photo ? 'Change photo' : 'Upload photo'}
          </button>
          {user?.profile_photo && (
            <button
              type="button"
              disabled={busy}
              onClick={onRemove}
              className="flex items-center gap-1.5 h-9 px-3 rounded-xl border border-slate-200 text-slate-600 text-xs font-bold hover:bg-slate-50 active:scale-95 transition-all disabled:opacity-60"
            >
              <Trash2 className="w-4 h-4" />
              Remove
            </button>
          )}
        </div>
        <p className="text-[11px] text-slate-500 mt-1.5">
          JPG, PNG or WebP, up to 5&nbsp;MB.
        </p>
        {error && <p className="text-[11px] text-rose-600 mt-1">{error}</p>}
        {message && <p className="text-[11px] text-emerald-600 mt-1">{message}</p>}
      </div>
    </div>
  );
};

export default ProfilePhotoUpload;
