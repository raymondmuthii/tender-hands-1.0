import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Route } from '@/routes/dashboard';
import { mockApi, resetApiMock, routeComponent } from './mock-api';

const { navigateMock } = vi.hoisted(() => ({ navigateMock: vi.fn() }));

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>();
  const { LinkStub } = await import('./link-stub');
  return { ...actual, useNavigate: () => navigateMock, Link: LinkStub } as unknown as typeof actual;
});

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api');
  const { mockApi: api } = await import('./mock-api');
  return { ...actual, api: api as unknown as typeof actual.api };
});

const Dashboard = routeComponent(Route);

const donorUser = {
  id: 1,
  full_name: 'Demo Donor',
  email: 'donor@test.com',
  phone: '+254722000099',
  role: 'donor' as const,
  created_at: '2026-01-01T00:00:00Z',
};

const donation = {
  id: 4,
  charity_id: 1,
  charity_name: 'Amani Learning Trust',
  amount: 5000,
  payment_method: 'M-PESA',
  mpesa_receipt: 'QHX001TEST',
  phone: '+254722000099',
  status: 'completed' as const,
  created_at: '2026-11-01T10:00:00Z',
};

beforeEach(() => {
  resetApiMock();
  navigateMock.mockReset();
  mockApi.auth.isLoggedIn.mockReturnValue(true);
  mockApi.auth.me.mockResolvedValue(donorUser);
});

describe('Donor dashboard', () => {
  it('renders the giving summary', async () => {
    mockApi.dashboard.summary.mockResolvedValue({
      total_donated: 21000,
      charities_supported: 3,
      monthly_giving: 1000,
      recent_donations: [],
    });

    render(<Dashboard />);

    expect(await screen.findByText(/Good morning, Demo\./)).toBeInTheDocument();
    expect(screen.getByText('KES 21,000')).toBeInTheDocument();
    expect(screen.getByText('Monthly giving')).toBeInTheDocument();
    expect(screen.getByText('KES 1,000')).toBeInTheDocument();
    expect(mockApi.dashboard.summary).toHaveBeenCalled();
  });

  it('renders the donation history', async () => {
    mockApi.donations.myHistory.mockResolvedValue([donation]);

    render(<Dashboard />);

    expect(await screen.findByText('Amani Learning Trust')).toBeInTheDocument();
    expect(screen.getByText('KES 5,000')).toBeInTheDocument();
    expect(screen.getByText('completed')).toBeInTheDocument();
    expect(screen.getByText('1 gifts')).toBeInTheDocument();
  });

  it('shows empty states when there is nothing to show', async () => {
    render(<Dashboard />);

    expect(await screen.findByText(/No donations yet\./i)).toBeInTheDocument();
    expect(screen.getByText(/No recurring donations yet\./i)).toBeInTheDocument();
  });

  it('sends admins to the admin dashboard', async () => {
    mockApi.auth.me.mockResolvedValue({ ...donorUser, role: 'admin' as const });

    render(<Dashboard />);

    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith({ to: '/admin' }));
  });

  it('asks logged-out visitors to sign in', async () => {
    mockApi.auth.isLoggedIn.mockReturnValue(false);

    render(<Dashboard />);

    expect(await screen.findByText(/Your giving space awaits\./i)).toBeInTheDocument();
    expect(mockApi.dashboard.summary).not.toHaveBeenCalled();
  });
});
