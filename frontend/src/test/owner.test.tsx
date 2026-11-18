import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Route } from '@/routes/owner';
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

const Owner = routeComponent(Route);

const charityUser = {
  id: 2,
  full_name: 'Charity Owner',
  email: 'owner@test.com',
  phone: '+254711000099',
  role: 'charity' as const,
  created_at: '2026-01-01T00:00:00Z',
};

const donorUser = { ...charityUser, id: 3, role: 'donor' as const };

const myCharity = {
  id: 'amani',
  slug: 'amani',
  name: 'Amani Learning Trust',
  category: 'Education',
  location: 'Kibera, Nairobi',
  description: 'Quality education for children in Kibera.',
  image: null,
  amount: 0,
  goal: 2000000,
  status: 'approved',
  is_featured: false,
  owner_id: 2,
  created_at: '2026-11-01T10:00:00Z',
};

beforeEach(() => {
  resetApiMock();
  navigateMock.mockReset();
});

describe('Owner route guards', () => {
  it('redirects logged-out visitors to /account', async () => {
    mockApi.auth.isLoggedIn.mockReturnValue(false);

    render(<Owner />);

    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith({ to: '/account' }));
    expect(mockApi.charities.mine).not.toHaveBeenCalled();
  });

  it('redirects a donor to the donor dashboard', async () => {
    mockApi.auth.isLoggedIn.mockReturnValue(true);
    mockApi.auth.me.mockResolvedValue(donorUser);

    render(<Owner />);

    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith({ to: '/dashboard' }));
    expect(mockApi.charities.mine).not.toHaveBeenCalled();
  });

  it('redirects an admin to the admin dashboard', async () => {
    mockApi.auth.isLoggedIn.mockReturnValue(true);
    mockApi.auth.me.mockResolvedValue({ ...charityUser, role: 'admin' as const });

    render(<Owner />);

    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith({ to: '/admin' }));
  });

  it('logs out and redirects when the token is rejected', async () => {
    mockApi.auth.isLoggedIn.mockReturnValue(true);
    mockApi.auth.me.mockRejectedValue(new Error('Token has expired.'));

    render(<Owner />);

    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith({ to: '/account' }));
    expect(mockApi.auth.logout).toHaveBeenCalled();
  });
});

describe('Owner workspace', () => {
  it('shows the application form before a charity exists', async () => {
    mockApi.auth.isLoggedIn.mockReturnValue(true);
    mockApi.auth.me.mockResolvedValue(charityUser);
    mockApi.charities.mine.mockResolvedValue(null);

    render(<Owner />);

    expect(await screen.findByText('Apply to join Tender Hands')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit application/i })).toBeInTheDocument();
  });

  it('shows the status badge and management tabs for an approved charity', async () => {
    mockApi.auth.isLoggedIn.mockReturnValue(true);
    mockApi.auth.me.mockResolvedValue(charityUser);
    mockApi.charities.mine.mockResolvedValue(myCharity);

    render(<Owner />);

    expect(await screen.findByText('Approved')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Impact stories' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Beneficiaries' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Inventory' })).toBeInTheDocument();
    await waitFor(() => expect(mockApi.charities.stories).toHaveBeenCalledWith('amani', { all: true }));
  });

  it('shows the pending badge while an application is under review', async () => {
    mockApi.auth.isLoggedIn.mockReturnValue(true);
    mockApi.auth.me.mockResolvedValue(charityUser);
    mockApi.charities.mine.mockResolvedValue({ ...myCharity, status: 'pending' });

    render(<Owner />);

    expect(await screen.findByText('Pending review')).toBeInTheDocument();
  });
});
