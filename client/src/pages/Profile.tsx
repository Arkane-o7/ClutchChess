import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore, UserRatingStats } from '../stores/auth';
import * as api from '../api/client';
import {
  RATING_MODES,
  formatModeName,
  getBelt,
  getBeltIconUrl,
  DEFAULT_RATING,
} from '../utils/ratings';
import type { ApiRatingStats } from '../api/types';

/**
 * User Profile page
 *
 * Allows users to view and edit their profile information.
 */
function Profile() {
  const navigate = useNavigate();
  const { user, setUser } = useAuthStore();

  const [username, setUsername] = useState(user?.username || '');
  const [isEditing, setIsEditing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Redirect if not logged in
  useEffect(() => {
    if (!user) {
      navigate('/login', { replace: true });
    }
  }, [user, navigate]);

  // Reset form when user changes
  useEffect(() => {
    if (user) {
      setUsername(user.username);
    }
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const trimmedUsername = username.trim();

    // Validate username
    if (trimmedUsername.length < 2) {
      setError('Username must be at least 2 characters');
      return;
    }

    if (trimmedUsername.length > 50) {
      setError('Username must be at most 50 characters');
      return;
    }

    // No change
    if (trimmedUsername === user?.username) {
      setIsEditing(false);
      return;
    }

    if (isSubmitting) return;
    setIsSubmitting(true);

    try {
      const updatedUser = await api.updateUser({ username: trimmedUsername });

      // Convert ratings to the proper format
      const ratings: Record<string, UserRatingStats> = {};
      for (const [mode, value] of Object.entries(updatedUser.ratings)) {
        if (typeof value === 'number') {
          ratings[mode] = { rating: value, games: 0, wins: 0 };
        } else {
          const stats = value as ApiRatingStats;
          ratings[mode] = { rating: stats.rating, games: stats.games, wins: stats.wins };
        }
      }

      // Update the store with the new user data
      setUser({
        id: updatedUser.id,
        username: updatedUser.username,
        email: updatedUser.email,
        pictureUrl: updatedUser.picture_url,
        ratings,
        isVerified: updatedUser.is_verified,
      });
      setIsEditing(false);
      setSuccess('Username updated successfully!');
    } catch (err) {
      if (err instanceof api.ApiClientError && err.detail) {
        if (err.detail.toLowerCase().includes('username')) {
          setError('This username is already taken. Please choose another.');
        } else {
          setError(err.detail);
        }
      } else {
        setError('Failed to update username. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setUsername(user?.username || '');
    setIsEditing(false);
    setError(null);
  };

  if (!user) {
    return null;
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Profile</h1>

        {error && <div className="auth-error" role="alert">{error}</div>}
        {success && <div className="auth-success" role="status">{success}</div>}

        <div className="profile-section">
          <div className="profile-field">
            <label>Email</label>
            <div className="profile-value">{user.email}</div>
          </div>

          <div className="profile-field">
            <label htmlFor="username">Username</label>
            {isEditing ? (
              <form onSubmit={handleSubmit} className="profile-edit-form">
                <input
                  type="text"
                  id="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  minLength={2}
                  maxLength={50}
                  autoComplete="username"
                  disabled={isSubmitting}
                  autoFocus
                />
                <div className="profile-edit-actions">
                  <button
                    type="submit"
                    className="btn btn-primary btn-sm"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? 'Saving...' : 'Save'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={handleCancel}
                    disabled={isSubmitting}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <div className="profile-value-row">
                <span className="profile-value">{user.username}</span>
                <button
                  type="button"
                  className="btn btn-link btn-sm"
                  onClick={() => setIsEditing(true)}
                >
                  Edit
                </button>
              </div>
            )}
          </div>

          <div className="profile-field">
            <label>Ratings</label>
            <div className="profile-ratings">
              {RATING_MODES.map((mode) => {
                const stats = user.ratings[mode] || { rating: DEFAULT_RATING, games: 0, wins: 0 };
                const belt = getBelt(stats.rating);
                return (
                  <div key={mode} className="profile-rating-card">
                    <img
                      src={getBeltIconUrl(belt)}
                      alt={belt}
                      className="belt-icon"
                    />
                    <div className="rating-mode">{formatModeName(mode)}</div>
                    <div className="rating-value">{stats.rating}</div>
                    {stats.games > 0 && (
                      <div className="rating-stats">
                        {stats.wins}W / {stats.games - stats.wins}L ({stats.games} games)
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Profile;
