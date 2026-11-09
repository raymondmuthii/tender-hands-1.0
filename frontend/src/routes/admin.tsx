import { useState, useEffect, useCallback } from 'react';
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import {
  LayoutDashboard, Users, HandHeart, BarChart3, LogOut,
  CheckCircle, XCircle, Star, StarOff, Loader2, RefreshCw,
  AlertCircle, ChevronLeft, ChevronRight, Search,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Brand } from '@/components/tender-hands/shared';
import { api, type AdminStats, type AdminCharity } from '@/lib/api';

export const Route = createFileRoute('/admin')({
  head: () => ({
    meta: [
      { title: 'Admin Dashboard | Tender Hands' },
      { name: 'robots', content: 'noindex' },
    ],
  }),
  component: AdminDashboard,
});

// ── Helpers ────────────────────────────────────────────────────────────────

const kes = (n: number) => `KES ${n.toLocaleString('en-KE')}`;

function fmt(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}

type Tab = 'overview' | 'pending' | 'approved' | 'rejected';

// ── Root component ─────────────────────────────────────────────────────────

function AdminDashboard() {
  const navigate = useNavigate();
  const [authChecked, setAuthChecked] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [tab, setTab] = useState<Tab>('overview');

  // Verify admin role client-side before rendering anything sensitive
  useEffect(() => {
    if (!api.auth.isLoggedIn()) {
      navigate({ to: '/account' });
      return;
    }
    api.auth.me().then(u => {
      if (u.role !== 'admin') {
        navigate({ to: '/dashboard' });
      } else {
        setIsAdmin(true);
      }
      setAuthChecked(true);
    }).catch(() => {
      navigate({ to: '/account' });
    });
  }, []);

  const handleLogout = () => {
    api.auth.logout();
    navigate({ to: '/' });
  };

  if (!authChecked) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="animate-spin text-primary" size={32} />
      </div>
    );
  }

  if (!isAdmin) return null;

  return (
    <div className="dashboard-layout">
      {/* Sidebar */}
      <aside className="dashboard-sidebar flex flex-col">
        <Brand />
        <p className="text-[9px] text-muted-foreground uppercase tracking-widest mt-9 mb-4 hidden sm:block">
          Admin panel
        </p>
        <nav className="flex flex-wrap sm:flex-col gap-2 mt-2" aria-label="Admin navigation">
          <NavBtn active={tab === 'overview'} onClick={() => setTab('overview')} icon={<BarChart3 size={15} />}>
            Overview
          </NavBtn>
          <NavBtn active={tab === 'pending'} onClick={() => setTab('pending')} icon={<AlertCircle size={15} />}>
            Pending
          </NavBtn>
          <NavBtn active={tab === 'approved'} onClick={() => setTab('approved')} icon={<CheckCircle size={15} />}>
            Approved
          </NavBtn>
          <NavBtn active={tab === 'rejected'} onClick={() => setTab('rejected')} icon={<XCircle size={15} />}>
            Rejected
          </NavBtn>
        </nav>

        <div className="mt-auto pt-8 flex flex-col gap-2">
          <Button variant="ghost" asChild className="justify-start">
            <Link to="/dashboard"><Users size={15} /> Donor view</Link>
          </Button>
          <Button variant="ghost" asChild className="justify-start">
            <Link to="/charities"><HandHeart size={15} /> Charities</Link>
          </Button>
          <Button variant="ghost" className="justify-start" onClick={handleLogout}>
            <LogOut size={15} /> Log out
          </Button>
        </div>
      </aside>

      {/* Main */}
      <main className="dashboard-main">
        <div className="flex items-center justify-between mb-8">
          <div>
            <p className="eyebrow">Tender Hands</p>
            <h1 className="text-[29px] mt-1">Admin Dashboard</h1>
          </div>
        </div>

        {tab === 'overview' && <OverviewTab />}
        {tab === 'pending' && <CharitiesTab status="pending" />}
        {tab === 'approved' && <CharitiesTab status="approved" />}
        {tab === 'rejected' && <CharitiesTab status="rejected" />}
      </main>
    </div>
  );
}

// ── Overview tab ───────────────────────────────────────────────────────────

function OverviewTab() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    api.admin.stats()
      .then(setStats)
      .catch(e => setError(e.message ?? 'Failed to load stats.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  if (loading) return <CenteredLoader />;
  if (error) return <ErrorCard message={error} onRetry={load} />;
  if (!stats) return null;

  const statCards = [
    { label: 'Total users', value: stats.total_users.toLocaleString(), icon: <Users size={15} /> },
    { label: 'Total charities', value: stats.total_charities.toLocaleString(), icon: <HandHeart size={15} /> },
    { label: 'Pending review', value: stats.pending_charities.toLocaleString(), icon: <AlertCircle size={15} />, highlight: stats.pending_charities > 0 },
    { label: 'Approved charities', value: stats.approved_charities.toLocaleString(), icon: <CheckCircle size={15} /> },
    { label: 'Total donations', value: stats.total_donations.toLocaleString(), icon: <BarChart3 size={15} /> },
    { label: 'Total raised', value: kes(stats.total_raised_kes), icon: <LayoutDashboard size={15} /> },
  ];

  return (
    <>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {statCards.map(({ label, value, icon, highlight }) => (
          <article
            key={label}
            className={`bg-card border rounded-md p-5 ${highlight ? 'border-primary/40 bg-primary/5' : 'border-border'}`}
          >
            <p className="text-xs text-muted-foreground flex justify-between items-center">
              {label}
              <span className={highlight ? 'text-primary' : 'text-muted-foreground'}>{icon}</span>
            </p>
            <p className={`text-2xl font-semibold mt-3 ${highlight ? 'text-primary' : ''}`}>{value}</p>
          </article>
        ))}
      </div>

      {stats.pending_charities > 0 && (
        <div className="bg-primary/5 border border-primary/20 rounded-md p-4 flex items-center gap-3">
          <AlertCircle size={18} className="text-primary shrink-0" />
          <div>
            <p className="text-sm font-medium">
              {stats.pending_charities} {stats.pending_charities === 1 ? 'charity' : 'charities'} waiting for review
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Go to the <button className="text-primary underline-offset-2 hover:underline" onClick={() => {}}>Pending</button> tab to approve or reject.
            </p>
          </div>
        </div>
      )}
    </>
  );
}

// ── Charities management tab ───────────────────────────────────────────────

function CharitiesTab({ status }: { status: 'pending' | 'approved' | 'rejected' }) {
  const [charities, setCharities] = useState<AdminCharity[]>([]);
  const [meta, setMeta] = useState({ total: 0, page: 1, per_page: 20, pages: 1 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const load = useCallback((page = 1) => {
    setLoading(true);
    setError('');
    api.admin.listCharities({ status, page, per_page: 20 })
      .then(({ data, meta }) => { setCharities(data); setMeta(meta); })
      .catch(e => setError(e.message ?? 'Failed to load charities.'))
      .finally(() => setLoading(false));
  }, [status]);

  useEffect(() => { load(1); }, [load]);

  const doAction = async (slug: string, action: 'approve' | 'reject' | 'feature') => {
    setActionLoading(slug + action);
    try {
      if (action === 'approve') await api.admin.approve(slug);
      else if (action === 'reject') await api.admin.reject(slug);
      else await api.admin.toggleFeature(slug);
      load(meta.page);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Action failed.');
    } finally {
      setActionLoading(null);
    }
  };

  const filtered = charities.filter(c =>
    `${c.name} ${c.location} ${c.category}`.toLowerCase().includes(search.toLowerCase())
  );

  const tabLabel = { pending: 'Pending Review', approved: 'Approved', rejected: 'Rejected' }[status];

  return (
    <>
      <div className="flex flex-wrap gap-3 items-center justify-between mb-5">
        <div>
          <h2 className="text-xl">{tabLabel} Charities</h2>
          <p className="text-xs text-muted-foreground mt-1">{meta.total} total</p>
        </div>
        <div className="flex gap-2 items-center">
          <div className="relative">
            <input
              className="!w-56 !py-2 !pl-8 !pr-3 text-xs"
              placeholder="Filter by name or location…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            <Search size={13} className="absolute left-2.5 top-2.5 text-muted-foreground" />
          </div>
          <Button variant="outline" size="sm" onClick={() => load(meta.page)}>
            <RefreshCw size={13} />
          </Button>
        </div>
      </div>

      {loading ? (
        <CenteredLoader />
      ) : error ? (
        <ErrorCard message={error} onRetry={() => load(1)} />
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground text-sm">
          {search ? 'No charities match your filter.' : `No ${status} charities.`}
        </div>
      ) : (
        <>
          <div className="bg-card border border-border rounded-md overflow-hidden">
            <div className="overflow-x-auto">
              <table className="donation-table">
                <thead>
                  <tr>
                    {['Name', 'Category', 'Location', 'Goal', 'Raised', 'Date', 'Actions'].map(h => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(c => (
                    <CharityRow
                      key={c.slug}
                      charity={c}
                      status={status}
                      actionLoading={actionLoading}
                      onAction={doAction}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {meta.pages > 1 && (
            <div className="flex items-center justify-between mt-4 text-xs text-muted-foreground">
              <span>Page {meta.page} of {meta.pages}</span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={meta.page <= 1}
                  onClick={() => load(meta.page - 1)}
                >
                  <ChevronLeft size={13} />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={meta.page >= meta.pages}
                  onClick={() => load(meta.page + 1)}
                >
                  <ChevronRight size={13} />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}

// ── Charity table row ──────────────────────────────────────────────────────

function CharityRow({
  charity: c,
  status,
  actionLoading,
  onAction,
}: {
  charity: AdminCharity;
  status: 'pending' | 'approved' | 'rejected';
  actionLoading: string | null;
  onAction: (slug: string, action: 'approve' | 'reject' | 'feature') => void;
}) {
  const busy = (action: string) => actionLoading === c.slug + action;

  return (
    <tr>
      <td>
        <div>
          <p className="font-medium">{c.name}</p>
          <p className="text-[10px] text-muted-foreground mt-0.5">{c.slug}</p>
        </div>
      </td>
      <td>
        <span className="text-[10px] text-primary bg-secondary px-2 py-1 rounded whitespace-nowrap">
          {c.category}
        </span>
      </td>
      <td className="text-muted-foreground">{c.location}</td>
      <td className="font-medium">{kes(c.goal)}</td>
      <td>{kes(c.amount)}</td>
      <td className="text-muted-foreground">{fmt(c.created_at)}</td>
      <td>
        <div className="flex gap-1">
          {status === 'pending' && (
            <>
              <ActionButton
                label="Approve"
                icon={<CheckCircle size={12} />}
                loading={busy('approve')}
                onClick={() => onAction(c.slug, 'approve')}
                className="text-primary"
              />
              <ActionButton
                label="Reject"
                icon={<XCircle size={12} />}
                loading={busy('reject')}
                onClick={() => onAction(c.slug, 'reject')}
                className="text-destructive"
              />
            </>
          )}
          {status === 'approved' && (
            <>
              <ActionButton
                label={c.is_featured ? 'Unfeature' : 'Feature'}
                icon={c.is_featured ? <StarOff size={12} /> : <Star size={12} />}
                loading={busy('feature')}
                onClick={() => onAction(c.slug, 'feature')}
                className={c.is_featured ? 'text-muted-foreground' : 'text-primary'}
              />
              <ActionButton
                label="Reject"
                icon={<XCircle size={12} />}
                loading={busy('reject')}
                onClick={() => onAction(c.slug, 'reject')}
                className="text-destructive"
              />
            </>
          )}
          {status === 'rejected' && (
            <ActionButton
              label="Re-approve"
              icon={<CheckCircle size={12} />}
              loading={busy('approve')}
              onClick={() => onAction(c.slug, 'approve')}
              className="text-primary"
            />
          )}
        </div>
      </td>
    </tr>
  );
}

// ── Micro-components ───────────────────────────────────────────────────────

function NavBtn({
  active, onClick, icon, children,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Button
      variant={active ? 'secondary' : 'ghost'}
      className="justify-start"
      onClick={onClick}
    >
      {icon} {children}
    </Button>
  );
}

function ActionButton({
  label, icon, loading, onClick, className = '',
}: {
  label: string;
  icon: React.ReactNode;
  loading: boolean;
  onClick: () => void;
  className?: string;
}) {
  return (
    <Button
      variant="ghost"
      size="sm"
      className={`h-7 px-2 text-[11px] gap-1 ${className}`}
      disabled={loading}
      onClick={onClick}
      title={label}
    >
      {loading ? <Loader2 size={11} className="animate-spin" /> : icon}
      <span className="hidden lg:inline">{label}</span>
    </Button>
  );
}

function CenteredLoader() {
  return (
    <div className="flex justify-center py-20">
      <Loader2 className="animate-spin text-primary" size={28} />
    </div>
  );
}

function ErrorCard({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 py-16 text-center">
      <AlertCircle size={24} className="text-destructive" />
      <p className="text-sm text-muted-foreground">{message}</p>
      <Button variant="outline" size="sm" onClick={onRetry}>
        <RefreshCw size={13} /> Try again
      </Button>
    </div>
  );
}
