import { Link } from 'react-router-dom';
import { staticUrl } from '../config';

interface PlayerBadgeProps {
  userId?: number | null;
  username: string;
  pictureUrl?: string | null;
  size?: 'sm' | 'md' | 'lg';
  linkToProfile?: boolean;
}

const SIZES = {
  sm: 24,
  md: 32,
  lg: 100,
};

function PlayerBadge({
  userId,
  username,
  pictureUrl,
  size = 'md',
  linkToProfile = true,
}: PlayerBadgeProps) {
  const px = SIZES[size];
  const imgSrc = pictureUrl || staticUrl('default-profile.jpg');

  const content = (
    <span className={`player-badge player-badge-${size}`}>
      <img
        className="player-badge-avatar"
        src={imgSrc}
        alt=""
        width={px}
        height={px}
      />
      <span className="player-badge-name">{username}</span>
    </span>
  );

  if (linkToProfile && userId) {
    return (
      <Link to={`/profile/${userId}`} className="player-badge-link">
        {content}
      </Link>
    );
  }

  return content;
}

export default PlayerBadge;
