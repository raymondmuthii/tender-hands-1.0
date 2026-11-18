import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { GivingProvider, useGiving } from '@/components/tender-hands/giving';
import { ApiError } from '@/lib/api';
import { mockApi, resetApiMock } from './mock-api';

vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-router')>();
  const { LinkStub } = await import('./link-stub');
  return { ...actual, Link: LinkStub } as unknown as typeof actual;
});

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api');
  const { mockApi: api } = await import('./mock-api');
  return { ...actual, api: api as unknown as typeof actual.api };
});

function Harness() {
  const { donate } = useGiving();
  return <button onClick={() => donate()}>Open donate dialog</button>;
}

function openDialog() {
  render(
    <GivingProvider>
      <Harness />
    </GivingProvider>,
  );
  fireEvent.click(screen.getByRole('button', { name: 'Open donate dialog' }));
}

beforeEach(() => {
  resetApiMock();
});

describe('Donation dialog', () => {
  it('prompts a logged-out visitor to sign in instead of donating', async () => {
    mockApi.auth.isLoggedIn.mockReturnValue(false);

    openDialog();

    expect(
      await screen.findByText(/Create a free account or log in to donate securely/i),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/Donation amount/i)).not.toBeInTheDocument();
  });

  it('does not call the API when the amount is not positive', async () => {
    mockApi.auth.isLoggedIn.mockReturnValue(true);

    openDialog();

    const amount = await screen.findByLabelText(/Donation amount/i);
    fireEvent.change(amount, { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: /send m-pesa request/i }));

    expect(mockApi.donations.create).not.toHaveBeenCalled();
  });

  it('sends the donation and shows the STK push confirmation', async () => {
    mockApi.auth.isLoggedIn.mockReturnValue(true);
    mockApi.donations.create.mockResolvedValue({
      donation_id: 12,
      status: 'pending',
      checkout_request_id: 'ws_CO_123',
      message: 'STK push sent.',
    });

    openDialog();

    fireEvent.change(await screen.findByLabelText(/Donation amount/i), {
      target: { value: '1500' },
    });
    fireEvent.change(screen.getByLabelText(/M-Pesa phone number/i), {
      target: { value: '+254722000099' },
    });
    fireEvent.click(screen.getByRole('button', { name: /send m-pesa request/i }));

    expect(
      await screen.findByText(/Check your phone for the M-Pesa prompt/i),
    ).toBeInTheDocument();
    expect(mockApi.donations.create).toHaveBeenCalledWith({
      charity_id: 'amani',
      amount: 1500,
      phone: '+254722000099',
    });
  });

  it('shows the API error when the donation request fails', async () => {
    mockApi.auth.isLoggedIn.mockReturnValue(true);
    mockApi.donations.create.mockRejectedValue(
      new ApiError('Charity not found or not approved.', 404),
    );

    openDialog();

    fireEvent.change(await screen.findByLabelText(/Donation amount/i), {
      target: { value: '1500' },
    });
    fireEvent.change(screen.getByLabelText(/M-Pesa phone number/i), {
      target: { value: '+254722000099' },
    });
    fireEvent.click(screen.getByRole('button', { name: /send m-pesa request/i }));

    expect(
      await screen.findByText('Charity not found or not approved.'),
    ).toBeInTheDocument();
  });
});
