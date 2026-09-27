// src/components/shared/UserAvatar.tsx
import React, { useState } from 'react';
import { mediaUrl } from '../../services/api';

interface UserAvatarProps {
  /**
   * Path as stored by the API, e.g. `/media/profile_photos/photo_user_10_ab.png`.
   * Resolved against the API origin - see `mediaUrl`.
   */
  src?: string | null;
  name?: string | null;
  /** Tailwind classes for the fallback initials chip. */
  className?: string;
  rounded?: string;
  textClassName?: string;
}

/**
 * Profile photo with an initials fallback.
 *
 * The API has always accepted and stored `users.profile_photo`, but the app
 * rendered initials everywhere and had no `<img>` at all, so an uploaded photo
 * was never visible. This keeps the existing initials chip as the fallback and
 * layers the real image on top once one exists.
 */
export const UserAvatar: React.FC<UserAvatarProps> = ({
  src,
  name,
  className = 'w-8 h-8',
  rounded = 'rounded-full',
  textClassName = 'text-xs',
}) => {
  // A photo can 404 (deleted from disk) or fail to decode; fall back silently.
  const [failed, setFailed] = useState(false);
  const initials = (name || '').trim().slice(0, 2).toUpperCase();
  const resolved = failed ? undefined : mediaUrl(src);

  if (!resolved) {
    return (
      <div
        className={`${className} ${rounded} bg-white/20 flex items-center justify-center font-bold ${textClassName}`}
        aria-hidden="true"
      >
        {initials || '—'}
      </div>
    );
  }

  return (
    <img
      src={resolved}
      alt=""
      onError={() => setFailed(true)}
      className={`${className} ${rounded} object-cover flex-shrink-0 bg-white/20`}
    />
  );
};

export default UserAvatar;
