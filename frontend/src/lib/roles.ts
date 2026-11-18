import type { User } from '@/lib/api';

/** The page each role is sent to after login or registration. */
export function routeForRole(role: User['role']): '/dashboard' | '/owner' | '/admin' {
  if (role === 'admin') return '/admin';
  if (role === 'charity') return '/owner';
  return '/dashboard';
}
