import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Route } from '@/routes/admin';
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

const Admin = routeComponent(Route);

const adminUser = {
  id: 9,
  full_name: 'TH Admin',
  email: 'admin@test.com',
  phone: null,
  role: 'admin' as const,
  created_at: '2026-01-01T00:00:00Z',
};

function charityFixture(overrides: Record<string, unknown>) {
  return {
    id: 'awaiting-org',
    slug: 'awaiting-org',
    name: 'Awaiting Org',
    category: 'Education',
    location: 'Nairobi',
    description: 'A charity awaiting review in the admin test suite.',
    image: null,
    amount: 0,
    goal: 100000,
    status: 'pending',
    is_featured: false,
    owner_id: 2,
    created_at: '2026-11-01T10:00:00Z',
    ...overrides,
  };
}

beforeEach(() => {
  resetApiMock();
  navigateMock.mockReset();
  mockApi.auth.isLoggedIn.mockReturnValue(true);
  mockApi.auth.me.mockResolvedValue(adminUser);
});

describe('Admin charity moderation', () => {
  it('approves a pending charity', async () => {
    mockApi.admin.listCharities.mockResolvedValue({
      data: [charityFixture({})],
      meta: { total: 1, page: 1, per_page: 20, pages: 1 },
    });

    render(<Admin />);
    fireEvent.click(await screen.findByRole('button', { name: 'Pending' }));

    expect(await screen.findByText('Awaiting Org')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }));

    await waitFor(() =>
      expect(mockApi.admin.approve).toHaveBeenCalledWith('awaiting-org'),
    );
  });

  it('rejects a pending charity', async () => {
    mockApi.admin.listCharities.mockResolvedValue({
      data: [charityFixture({})],
      meta: { total: 1, page: 1, per_page: 20, pages: 1 },
    });

    render(<Admin />);
    fireEvent.click(await screen.findByRole('button', { name: 'Pending' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Reject' }));

    await waitFor(() =>
      expect(mockApi.admin.reject).toHaveBeenCalledWith('awaiting-org'),
    );
  });

  it('toggles the featured flag of an approved charity', async () => {
    mockApi.admin.listCharities.mockResolvedValue({
      data: [charityFixture({ slug: 'amani', id: 'amani', name: 'Amani', status: 'approved' })],
      meta: { total: 1, page: 1, per_page: 20, pages: 1 },
    });

    render(<Admin />);
    fireEvent.click(await screen.findByRole('button', { name: 'Approved' }));
    fireEvent.click(await screen.findByRole('button', { name: /feature/i }));

    await waitFor(() =>
      expect(mockApi.admin.toggleFeature).toHaveBeenCalledWith('amani'),
    );
  });

  it('shows platform statistics on the overview tab', async () => {
    mockApi.admin.stats.mockResolvedValue({
      total_users: 12,
      total_charities: 4,
      pending_charities: 0,
      approved_charities: 4,
      total_donations: 5,
      total_raised_kes: 21000,
    });

    render(<Admin />);

    expect(await screen.findByText('Admin Dashboard')).toBeInTheDocument();
    expect(await screen.findByText('KES 21,000')).toBeInTheDocument();
    expect(screen.getByText('Total users')).toBeInTheDocument();
  });

  it('redirects non-admins away', async () => {
    mockApi.auth.me.mockResolvedValue({ ...adminUser, role: 'donor' as const });

    render(<Admin />);

    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith({ to: '/dashboard' }));
    expect(mockApi.admin.stats).not.toHaveBeenCalled();
  });
});
