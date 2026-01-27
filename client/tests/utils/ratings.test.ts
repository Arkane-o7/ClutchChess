/**
 * Tests for rating and belt utilities
 */

import { describe, it, expect } from 'vitest';
import {
  getBelt,
  getBeltDisplayName,
  getBeltIconUrl,
  getBeltIconUrlForRating,
  formatModeName,
  formatModeNameShort,
  formatRatingChange,
  getRatingChangeClass,
  DEFAULT_RATING,
  RATING_MODES,
} from '../../src/utils/ratings';

describe('getBelt', () => {
  it('returns "none" for null rating', () => {
    expect(getBelt(null)).toBe('none');
  });

  it('returns "none" for undefined rating', () => {
    expect(getBelt(undefined)).toBe('none');
  });

  it('returns "white" for rating 0', () => {
    expect(getBelt(0)).toBe('white');
  });

  it('returns "white" for rating below 900', () => {
    expect(getBelt(100)).toBe('white');
    expect(getBelt(500)).toBe('white');
    expect(getBelt(899)).toBe('white');
  });

  it('returns "yellow" for rating 900-1099', () => {
    expect(getBelt(900)).toBe('yellow');
    expect(getBelt(1000)).toBe('yellow');
    expect(getBelt(1099)).toBe('yellow');
  });

  it('returns "green" for rating 1100-1299', () => {
    expect(getBelt(1100)).toBe('green');
    expect(getBelt(1200)).toBe('green');
    expect(getBelt(1299)).toBe('green');
  });

  it('returns "purple" for rating 1300-1499', () => {
    expect(getBelt(1300)).toBe('purple');
    expect(getBelt(1400)).toBe('purple');
    expect(getBelt(1499)).toBe('purple');
  });

  it('returns "orange" for rating 1500-1699', () => {
    expect(getBelt(1500)).toBe('orange');
    expect(getBelt(1600)).toBe('orange');
    expect(getBelt(1699)).toBe('orange');
  });

  it('returns "blue" for rating 1700-1899', () => {
    expect(getBelt(1700)).toBe('blue');
    expect(getBelt(1800)).toBe('blue');
    expect(getBelt(1899)).toBe('blue');
  });

  it('returns "brown" for rating 1900-2099', () => {
    expect(getBelt(1900)).toBe('brown');
    expect(getBelt(2000)).toBe('brown');
    expect(getBelt(2099)).toBe('brown');
  });

  it('returns "red" for rating 2100-2299', () => {
    expect(getBelt(2100)).toBe('red');
    expect(getBelt(2200)).toBe('red');
    expect(getBelt(2299)).toBe('red');
  });

  it('returns "black" for rating 2300+', () => {
    expect(getBelt(2300)).toBe('black');
    expect(getBelt(2500)).toBe('black');
    expect(getBelt(3000)).toBe('black');
  });
});

describe('getBeltDisplayName', () => {
  it('capitalizes first letter', () => {
    expect(getBeltDisplayName('black')).toBe('Black');
    expect(getBeltDisplayName('white')).toBe('White');
    expect(getBeltDisplayName('none')).toBe('None');
  });

  it('handles single character', () => {
    expect(getBeltDisplayName('a')).toBe('A');
  });

  it('handles empty string', () => {
    expect(getBeltDisplayName('')).toBe('');
  });
});

describe('getBeltIconUrl', () => {
  it('returns correct URL format for belt', () => {
    expect(getBeltIconUrl('black')).toBe(
      'https://com-kfchess-public.s3.amazonaws.com/static/belt-black.png'
    );
    expect(getBeltIconUrl('white')).toBe(
      'https://com-kfchess-public.s3.amazonaws.com/static/belt-white.png'
    );
    expect(getBeltIconUrl('none')).toBe(
      'https://com-kfchess-public.s3.amazonaws.com/static/belt-none.png'
    );
  });
});

describe('getBeltIconUrlForRating', () => {
  it('returns correct icon URL for rating', () => {
    expect(getBeltIconUrlForRating(1200)).toBe(
      'https://com-kfchess-public.s3.amazonaws.com/static/belt-green.png'
    );
    expect(getBeltIconUrlForRating(2300)).toBe(
      'https://com-kfchess-public.s3.amazonaws.com/static/belt-black.png'
    );
  });

  it('handles null rating', () => {
    expect(getBeltIconUrlForRating(null)).toBe(
      'https://com-kfchess-public.s3.amazonaws.com/static/belt-none.png'
    );
  });

  it('handles undefined rating', () => {
    expect(getBeltIconUrlForRating(undefined)).toBe(
      'https://com-kfchess-public.s3.amazonaws.com/static/belt-none.png'
    );
  });
});

describe('formatModeName', () => {
  it('formats "2p_standard" correctly', () => {
    expect(formatModeName('2p_standard')).toBe('2-Player Standard');
  });

  it('formats "2p_lightning" correctly', () => {
    expect(formatModeName('2p_lightning')).toBe('2-Player Lightning');
  });

  it('formats "4p_standard" correctly', () => {
    expect(formatModeName('4p_standard')).toBe('4-Player Standard');
  });

  it('formats "4p_lightning" correctly', () => {
    expect(formatModeName('4p_lightning')).toBe('4-Player Lightning');
  });

  it('returns original string for invalid format', () => {
    expect(formatModeName('invalid')).toBe('invalid');
    expect(formatModeName('no_underscore_count')).toBe('no_underscore_count');
  });
});

describe('formatModeNameShort', () => {
  it('formats "2p_standard" as "2P Std"', () => {
    expect(formatModeNameShort('2p_standard')).toBe('2P Std');
  });

  it('formats "2p_lightning" as "2P Ltng"', () => {
    expect(formatModeNameShort('2p_lightning')).toBe('2P Ltng');
  });

  it('formats "4p_standard" as "4P Std"', () => {
    expect(formatModeNameShort('4p_standard')).toBe('4P Std');
  });

  it('formats "4p_lightning" as "4P Ltng"', () => {
    expect(formatModeNameShort('4p_lightning')).toBe('4P Ltng');
  });

  it('returns original string for invalid format', () => {
    expect(formatModeNameShort('invalid')).toBe('invalid');
  });
});

describe('formatRatingChange', () => {
  it('returns "+15" for positive change', () => {
    expect(formatRatingChange(1200, 1215)).toBe('+15');
  });

  it('returns "-8" for negative change', () => {
    expect(formatRatingChange(1200, 1192)).toBe('-8');
  });

  it('returns "0" for no change', () => {
    expect(formatRatingChange(1200, 1200)).toBe('0');
  });

  it('handles large changes', () => {
    expect(formatRatingChange(1000, 1100)).toBe('+100');
    expect(formatRatingChange(1500, 1200)).toBe('-300');
  });
});

describe('getRatingChangeClass', () => {
  it('returns positive class for rating increase', () => {
    expect(getRatingChangeClass(1200, 1215)).toBe('rating-change-positive');
  });

  it('returns negative class for rating decrease', () => {
    expect(getRatingChangeClass(1200, 1185)).toBe('rating-change-negative');
  });

  it('returns neutral class for no change', () => {
    expect(getRatingChangeClass(1200, 1200)).toBe('rating-change-neutral');
  });
});

describe('constants', () => {
  it('DEFAULT_RATING is 1200', () => {
    expect(DEFAULT_RATING).toBe(1200);
  });

  it('RATING_MODES contains all four modes', () => {
    expect(RATING_MODES).toEqual([
      '2p_standard',
      '2p_lightning',
      '4p_standard',
      '4p_lightning',
    ]);
  });
});
