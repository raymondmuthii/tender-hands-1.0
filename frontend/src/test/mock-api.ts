/**
 * Shared stand-in for src/lib/api.ts used by the component tests.
 *
 * Each test file mocks `@/lib/api` and swaps in this object, then sets the
 * return values it needs. `resetApiMock()` restores sensible empty defaults.
 */
import type { ComponentType } from 'react';
import { vi, type Mock } from 'vitest';

const fn = () => vi.fn();

export const mockApi = {
  auth: {
    register: fn(),
    login: fn(),
    me: fn(),
    updateMe: fn(),
    refresh: fn(),
    logout: vi.fn(),
    isLoggedIn: vi.fn(),
  },
  charities: {
    list: fn(),
    get: fn(),
    mine: fn(),
    apply: fn(),
    update: fn(),
    stories: fn(),
    createStory: fn(),
    updateStory: fn(),
    deleteStory: fn(),
    beneficiaries: fn(),
    createBeneficiary: fn(),
    updateBeneficiary: fn(),
    deleteBeneficiary: fn(),
    inventory: fn(),
    createInventoryItem: fn(),
    updateInventoryItem: fn(),
    deleteInventoryItem: fn(),
  },
  donations: { create: fn(), myHistory: fn(), receipt: fn() },
  dashboard: { summary: fn() },
  recurring: { list: fn(), create: fn(), update: fn(), cancel: fn() },
  admin: { stats: fn(), listCharities: fn(), approve: fn(), reject: fn(), toggleFeature: fn() },
};

export function resetApiMock() {
  for (const group of Object.values(mockApi)) {
    for (const method of Object.values(group) as unknown as Mock[]) {
      method.mockReset();
    }
  }

  mockApi.auth.isLoggedIn.mockReturnValue(false);
  mockApi.charities.list.mockResolvedValue({
    data: [],
    meta: { total: 0, page: 1, per_page: 12, pages: 0 },
  });
  mockApi.charities.mine.mockResolvedValue(null);
  mockApi.charities.stories.mockResolvedValue([]);
  mockApi.charities.beneficiaries.mockResolvedValue([]);
  mockApi.charities.inventory.mockResolvedValue([]);
  mockApi.donations.myHistory.mockResolvedValue([]);
  mockApi.recurring.list.mockResolvedValue([]);
  mockApi.dashboard.summary.mockResolvedValue({
    total_donated: 0,
    charities_supported: 0,
    monthly_giving: 0,
    recent_donations: [],
  });
  mockApi.admin.listCharities.mockResolvedValue({
    data: [],
    meta: { total: 0, page: 1, per_page: 20, pages: 0 },
  });
  mockApi.admin.stats.mockResolvedValue({
    total_users: 0,
    total_charities: 0,
    pending_charities: 0,
    approved_charities: 0,
    total_donations: 0,
    total_raised_kes: 0,
  });
}

/** Reads a file route's component so tests can render it directly. */
export function routeComponent(route: unknown): ComponentType {
  return (route as { options: { component: ComponentType } }).options.component;
}
