import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Route } from '@/routes/account';
import { ApiError } from '@/lib/api';
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

const Account = routeComponent(Route);

const donorUser = {
  id: 1,
  full_name: 'Demo Donor',
  email: 'donor@test.com',
  phone: '+254722000099',
  role: 'donor' as const,
  created_at: '2026-01-01T00:00:00Z',
};

const charityUser = {
  id: 2,
  full_name: 'New Charity',
  email: 'new@charity.ke',
  phone: null,
  role: 'charity' as const,
  created_at: '2026-01-01T00:00:00Z',
};

function fillLogin(identifier: string, password: string) {
  fireEvent.change(screen.getByPlaceholderText(/or \+254712345678/), {
    target: { value: identifier },
  });
  fireEvent.change(screen.getByPlaceholderText('Enter your password'), {
    target: { value: password },
  });
}

function fillRegister(overrides: { role?: 'donor' | 'charity' } = {}) {
  fireEvent.change(screen.getByPlaceholderText('Njeri Wanjiku'), {
    target: { value: 'New Charity' },
  });
  fireEvent.change(screen.getByPlaceholderText('njeri.wanjiku@gmail.com'), {
    target: { value: 'new@charity.ke' },
  });
  fireEvent.change(screen.getByPlaceholderText('At least 8 chars, a number and symbol'), {
    target: { value: 'Owner@1234!' },
  });
  if (overrides.role === 'charity') {
    fireEvent.click(screen.getByLabelText(/I'm registering a charity/i));
  }
  fireEvent.click(screen.getByRole('checkbox', { name: /I agree/i }));
}

beforeEach(() => {
  resetApiMock();
  navigateMock.mockReset();
});

describe('Account login', () => {
  it('logs in and sends a donor to the donor dashboard', async () => {
    mockApi.auth.login.mockResolvedValue({
      user: donorUser,
      access_token: 'access',
      refresh_token: 'refresh',
    });

    render(<Account />);
    fillLogin('donor@test.com', 'Donor@1234!');
    fireEvent.click(screen.getByRole('button', { name: /log in/i }));

    await waitFor(() =>
      expect(mockApi.auth.login).toHaveBeenCalledWith('donor@test.com', 'Donor@1234!'),
    );
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith({ to: '/dashboard' }));
  });

  it('sends a charity owner to /owner after login', async () => {
    mockApi.auth.login.mockResolvedValue({
      user: charityUser,
      access_token: 'access',
      refresh_token: 'refresh',
    });

    render(<Account />);
    fillLogin('new@charity.ke', 'Owner@1234!');
    fireEvent.click(screen.getByRole('button', { name: /log in/i }));

    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith({ to: '/owner' }));
  });

  it('shows the API message when login fails and stays on the page', async () => {
    mockApi.auth.login.mockRejectedValue(new ApiError('Invalid credentials.', 401));

    render(<Account />);
    fillLogin('donor@test.com', 'WrongPass@1');
    fireEvent.click(screen.getByRole('button', { name: /log in/i }));

    expect(await screen.findByText('Invalid credentials.')).toBeInTheDocument();
    expect(navigateMock).not.toHaveBeenCalled();
  });
});

describe('Account registration', () => {
  it('registers as a donor by default', async () => {
    mockApi.auth.register.mockResolvedValue({
      user: donorUser,
      access_token: 'access',
      refresh_token: 'refresh',
    });

    render(<Account />);
    fillRegister();
    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() =>
      expect(mockApi.auth.register).toHaveBeenCalledWith(
        expect.objectContaining({ email: 'new@charity.ke', role: 'donor' }),
      ),
    );
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith({ to: '/dashboard' }));
  });

  it('sends role "charity" when the user is registering a charity', async () => {
    mockApi.auth.register.mockResolvedValue({
      user: charityUser,
      access_token: 'access',
      refresh_token: 'refresh',
    });

    render(<Account />);
    fillRegister({ role: 'charity' });
    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() =>
      expect(mockApi.auth.register).toHaveBeenCalledWith(
        expect.objectContaining({ role: 'charity' }),
      ),
    );
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith({ to: '/owner' }));
  });

  it('surfaces the first validation error from the API', async () => {
    mockApi.auth.register.mockRejectedValue(
      new ApiError('Validation failed.', 422, {
        password: ['Password must contain at least one number.'],
      }),
    );

    render(<Account />);
    fillRegister();
    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    expect(
      await screen.findByText('Password must contain at least one number.'),
    ).toBeInTheDocument();
    expect(navigateMock).not.toHaveBeenCalled();
  });
});
