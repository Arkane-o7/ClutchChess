import { getBeltDisplayName, getBeltIconUrl } from '../utils/ratings';

interface BeltIconProps {
  belt: string;
  size?: 'sm' | 'md' | 'lg';
}

const SIZE_CLASSES = {
  sm: 'belt-icon belt-icon-sm',
  md: 'belt-icon',
  lg: 'belt-icon belt-icon-lg',
};

function BeltIcon({ belt, size = 'md' }: BeltIconProps) {
  if (belt === 'none') {
    return null;
  }

  const label = `${getBeltDisplayName(belt)} Belt`;

  return (
    <span className="belt-icon-wrapper" tabIndex={0}>
      <img
        src={getBeltIconUrl(belt)}
        alt={label}
        className={SIZE_CLASSES[size]}
      />
      <span className="belt-icon-tooltip" role="tooltip">{label}</span>
    </span>
  );
}

export default BeltIcon;
