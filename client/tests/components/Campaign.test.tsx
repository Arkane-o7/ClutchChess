/**
 * Campaign Page Component Tests
 *
 * Basic tests for authentication and rendering.
 * The store tests in tests/stores/campaign.test.ts cover the detailed store behavior.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Campaign from '../../src/pages/Campaign';
import { useAuthStore } from '../../src/stores/auth';
import { useCampaignStore } from '../../src/stores/campaign';

// Mock the navigate function
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock API to prevent actual network calls
vi.mock('../../src/api/client', () => ({
  getCampaignProgress: vi.fn().mockImplementation(() => new Promise(() => {})),
  getCampaignLevels: vi.fn().mockImplementation(() => new Promise(() => {})),
  startCampaignLevel: vi.fn(),
  ApiClientError: class ApiClientError extends Error {
    constructor(
      message: string,
      public status: number,
      public detail?: string
    ) {
      super(message);
    }
  },
}));

function renderCampaign() {
  return render(
    <MemoryRouter>
      <Campaign />
    </MemoryRouter>
  );
}

describe('Campaign Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();

    // Default authenticated state
    useAuthStore.setState({
      user: {
        id: 1,
        username: 'testuser',
        email: 'test@test.com',
        pictureUrl: null,
        ratings: {},
        isVerified: true,
      },
      isAuthenticated: true,
      isLoading: false,
      error: null,
    });

    useCampaignStore.getState().reset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('authentication', () => {
    it('redirects to login when not authenticated', () => {
      useAuthStore.setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });

      renderCampaign();

      expect(mockNavigate).toHaveBeenCalledWith('/login?next=/campaign');
    });

    it('shows loading while checking auth', () => {
      useAuthStore.setState({
        user: null,
        isAuthenticated: false,
        isLoading: true,
      });

      renderCampaign();

      expect(screen.getByText('Loading...')).toBeInTheDocument();
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('does not redirect when authenticated', () => {
      renderCampaign();

      expect(mockNavigate).not.toHaveBeenCalledWith('/login?next=/campaign');
    });
  });

  describe('content display', () => {
    it('renders page header', () => {
      renderCampaign();

      expect(screen.getByText('Campaign Mode')).toBeInTheDocument();
      expect(
        screen.getByText('Complete missions to earn your belts!')
      ).toBeInTheDocument();
    });

    it('shows loading state while fetching', () => {
      renderCampaign();

      expect(screen.getByText('Loading campaign...')).toBeInTheDocument();
    });
  });
});
