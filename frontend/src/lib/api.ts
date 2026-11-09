/**
 * Tender Hands API client
 *
 * Single source of truth for all backend communication.
 * Base URL is controlled by the VITE_API_URL environment variable.
 *
 * Usage:
 *   import { api } from '@/lib/api'
 *   const charities = await api.charities.list({ category: 'Education' })
 */

const BASE_URL = (import.meta.env['VITE_API_URL'] ?? 'http://localhost:5000').replace(/\/$/, '');

// ── Helpers ────────────────────────────────────────────────────────────────

const isBrowser = typeof window !== 'undefined';

function getToken(): string | null {
  return isBrowser ? localStorage.getItem('access_token') : null;
}

function saveTokens(access: string, refresh: string) {
  if (!isBrowser) return;
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
}

function clearTokens() {
  if (!isBrowser) return;
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

class ApiError extends Error {
  status: number;
  errors?: Record<string, string[]>;

  constructor(message: string, status: number, errors?: Record<string, string[]>) {
    super(message);
    this.status = status;
    if (errors !== undefined) this.errors = errors;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  authenticated = false,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (authenticated) {
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  const json = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new ApiError(
      json.message ?? 'An unexpected error occurred.',
      res.status,
      json.errors,
    );
  }

  return json.data as T;
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface Charity {
  id: string;          // slug, e.g. "amani"
  name: string;
  category: string;
  location: string;
  description: string;
  image: string | null;
  amount: number;      // amount_raised in KES
  goal: number;        // goal_amount in KES
  status: string;
  is_featured: boolean;
  slug: string;
}

export interface CharityListMeta {
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface User {
  id: number;
  full_name: string;
  email: string;
  phone: string | null;
  role: 'donor' | 'charity' | 'admin';
  created_at: string;
}

export interface Donation {
  id: number;
  charity_id: number;
  charity_name: string;
  amount: number;
  payment_method: string;
  mpesa_receipt: string | null;
  phone: string;
  status: 'pending' | 'completed' | 'failed';
  created_at: string;
}

export interface DashboardSummary {
  total_donated: number;
  charities_supported: number;
  monthly_giving: number;
  recent_donations: Donation[];
}

export interface RecurringDonation {
  id: number;
  charity_id: number;
  charity_name: string;
  amount: number;
  frequency: string;
  next_run_date: string;
  status: 'active' | 'paused' | 'cancelled';
  created_at: string;
}

export interface AdminStats {
  total_users: number;
  total_charities: number;
  pending_charities: number;
  approved_charities: number;
  total_donations: number;
  total_raised_kes: number;
}

export interface AdminCharity extends Charity {
  owner_id: number;
  created_at: string;
}

// ── API surface ────────────────────────────────────────────────────────────

export const api = {

  // ── Auth ──────────────────────────────────────────────────────────────

  auth: {
    async register(data: {
      full_name: string;
      email: string;
      password: string;
      phone?: string;
      role?: 'donor' | 'charity';
    }): Promise<{ user: User; access_token: string; refresh_token: string }> {
      const result = await request<{ user: User; access_token: string; refresh_token: string }>(
        '/api/auth/register',
        { method: 'POST', body: JSON.stringify(data) },
      );
      saveTokens(result.access_token, result.refresh_token);
      return result;
    },

    async login(
      identifier: string,
      password: string,
    ): Promise<{ user: User; access_token: string; refresh_token: string }> {
      const result = await request<{ user: User; access_token: string; refresh_token: string }>(
        '/api/auth/login',
        { method: 'POST', body: JSON.stringify({ identifier, password }) },
      );
      saveTokens(result.access_token, result.refresh_token);
      return result;
    },

    async me(): Promise<User> {
      return request<User>('/api/auth/me', {}, true);
    },

    async updateMe(data: { full_name?: string; phone?: string; password?: string }): Promise<User> {
      return request<User>('/api/auth/me', { method: 'PATCH', body: JSON.stringify(data) }, true);
    },

    async refresh(): Promise<string> {
      const refreshToken = isBrowser ? localStorage.getItem('refresh_token') : null;
      const result = await request<{ access_token: string }>('/api/auth/refresh', {
        method: 'POST',
        headers: { Authorization: `Bearer ${refreshToken}` },
      });
      if (isBrowser) localStorage.setItem('access_token', result.access_token);
      return result.access_token;
    },

    logout() {
      clearTokens();
    },

    isLoggedIn(): boolean {
      return !!getToken();
    },
  },

  // ── Charities ─────────────────────────────────────────────────────────

  charities: {
    async list(params?: {
      category?: string;
      search?: string;
      featured?: boolean;
      page?: number;
      per_page?: number;
    }): Promise<{ data: Charity[]; meta: CharityListMeta }> {
      const qs = new URLSearchParams();
      if (params?.category) qs.set('category', params.category);
      if (params?.search) qs.set('search', params.search);
      if (params?.featured) qs.set('featured', 'true');
      if (params?.page) qs.set('page', String(params.page));
      if (params?.per_page) qs.set('per_page', String(params.per_page));

      const query = qs.toString() ? `?${qs}` : '';
      const res = await fetch(`${BASE_URL}/api/charities${query}`);
      const json = await res.json();
      if (!res.ok) throw new ApiError(json.message ?? 'Failed to load charities.', res.status);
      return { data: json.data as Charity[], meta: json.meta as CharityListMeta };
    },

    async get(slug: string): Promise<Charity> {
      return request<Charity>(`/api/charities/${slug}`);
    },

    async apply(data: {
      name: string;
      slug: string;
      category: string;
      location: string;
      description: string;
      goal_amount: number;
      image_url?: string;
    }): Promise<Charity> {
      return request<Charity>('/api/charities', { method: 'POST', body: JSON.stringify(data) }, true);
    },

    async update(slug: string, data: Partial<{
      name: string;
      category: string;
      location: string;
      description: string;
      goal_amount: number;
      image_url: string;
    }>): Promise<Charity> {
      return request<Charity>(
        `/api/charities/${slug}`,
        { method: 'PATCH', body: JSON.stringify(data) },
        true,
      );
    },
  },

  // ── Donations ─────────────────────────────────────────────────────────

  donations: {
    async create(data: {
      charity_id: string;   // slug
      amount: number;
      phone: string;
    }): Promise<{ donation_id: number; status: string; checkout_request_id: string; message: string }> {
      return request('/api/donations', { method: 'POST', body: JSON.stringify(data) }, true);
    },

    async myHistory(): Promise<Donation[]> {
      return request<Donation[]>('/api/donations/me', {}, true);
    },

    async receipt(donationId: number): Promise<Donation & { charity_name: string }> {
      return request(`/api/donations/${donationId}/receipt`, {}, true);
    },
  },

  // ── Dashboard ─────────────────────────────────────────────────────────

  dashboard: {
    async summary(): Promise<DashboardSummary> {
      return request<DashboardSummary>('/api/dashboard/summary', {}, true);
    },
  },

  // ── Recurring ─────────────────────────────────────────────────────────

  recurring: {
    async list(): Promise<RecurringDonation[]> {
      return request<RecurringDonation[]>('/api/recurring', {}, true);
    },

    async create(data: {
      charity_id: string;
      amount: number;
      next_run_date: string;   // YYYY-MM-DD
      frequency?: 'monthly';
    }): Promise<RecurringDonation> {
      return request<RecurringDonation>('/api/recurring', { method: 'POST', body: JSON.stringify(data) }, true);
    },

    async update(
      id: number,
      data: { amount?: number; status?: 'active' | 'paused' | 'cancelled'; next_run_date?: string },
    ): Promise<RecurringDonation> {
      return request<RecurringDonation>(
        `/api/recurring/${id}`,
        { method: 'PATCH', body: JSON.stringify(data) },
        true,
      );
    },

    async cancel(id: number): Promise<void> {
      await request(`/api/recurring/${id}`, { method: 'DELETE' }, true);
    },
  },

  // ── Admin ──────────────────────────────────────────────────────────────

  admin: {
    async stats(): Promise<AdminStats> {
      return request<AdminStats>('/api/admin/stats', {}, true);
    },

    async listCharities(params?: {
      status?: 'pending' | 'approved' | 'rejected';
      page?: number;
      per_page?: number;
    }): Promise<{ data: AdminCharity[]; meta: CharityListMeta }> {
      const qs = new URLSearchParams();
      if (params?.status) qs.set('status', params.status);
      if (params?.page) qs.set('page', String(params.page));
      if (params?.per_page) qs.set('per_page', String(params.per_page));
      const query = qs.toString() ? `?${qs}` : '';
      const res = await fetch(`${BASE_URL}/api/admin/charities${query}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      const json = await res.json();
      if (!res.ok) throw new ApiError(json.message ?? 'Failed.', res.status);
      return { data: json.data as AdminCharity[], meta: json.meta as CharityListMeta };
    },

    async approve(slug: string): Promise<AdminCharity> {
      return request<AdminCharity>(`/api/admin/charities/${slug}/approve`, { method: 'POST' }, true);
    },

    async reject(slug: string): Promise<AdminCharity> {
      return request<AdminCharity>(`/api/admin/charities/${slug}/reject`, { method: 'POST' }, true);
    },

    async toggleFeature(slug: string): Promise<{ slug: string; is_featured: boolean }> {
      return request(`/api/admin/charities/${slug}/feature`, { method: 'POST' }, true);
    },
  },
};

export { ApiError };
