import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import PlayerBadge from '../../src/components/PlayerBadge';

function renderBadge(props: React.ComponentProps<typeof PlayerBadge>) {
  return render(
    <BrowserRouter>
      <PlayerBadge {...props} />
    </BrowserRouter>
  );
}

describe('PlayerBadge', () => {
  it('renders username', () => {
    renderBadge({ username: 'alice' });
    expect(screen.getByText('alice')).toBeInTheDocument();
  });

  it('renders avatar image', () => {
    const { container } = renderBadge({ username: 'alice', pictureUrl: 'https://example.com/pic.jpg' });
    const img = container.querySelector('.player-badge-avatar') as HTMLImageElement;
    expect(img).toHaveAttribute('src', 'https://example.com/pic.jpg');
  });

  it('uses default profile image when pictureUrl is null', () => {
    const { container } = renderBadge({ username: 'alice', pictureUrl: null });
    const img = container.querySelector('.player-badge-avatar') as HTMLImageElement;
    expect(img.getAttribute('src')).toContain('default-profile.jpg');
  });

  it('links to profile when userId is provided', () => {
    renderBadge({ username: 'alice', userId: 42 });
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/profile/42');
  });

  it('does not link when userId is null', () => {
    renderBadge({ username: 'AI Bot', userId: null });
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('does not link when linkToProfile is false', () => {
    renderBadge({ username: 'alice', userId: 42, linkToProfile: false });
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('applies size class', () => {
    renderBadge({ username: 'alice', size: 'lg' });
    const badge = screen.getByText('alice').closest('.player-badge');
    expect(badge).toHaveClass('player-badge-lg');
  });

  it('sets correct image dimensions for sm size', () => {
    const { container } = renderBadge({ username: 'alice', size: 'sm' });
    const img = container.querySelector('.player-badge-avatar')!;
    expect(img).toHaveAttribute('width', '24');
    expect(img).toHaveAttribute('height', '24');
  });

  it('defaults to md size', () => {
    const { container } = renderBadge({ username: 'alice' });
    const badge = screen.getByText('alice').closest('.player-badge');
    expect(badge).toHaveClass('player-badge-md');
    const img = container.querySelector('.player-badge-avatar')!;
    expect(img).toHaveAttribute('width', '32');
  });
});
