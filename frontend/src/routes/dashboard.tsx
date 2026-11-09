import { useState, useEffect } from 'react';
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import {
  ArrowUpRight, Download, Heart, LayoutDashboard, Search,
  Repeat, HandHeart, LogOut, BadgeCheck, ReceiptText, Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Brand } from '@/components/tender-hands/shared';
import { useGiving } from '@/components/tender-hands/giving';
import { kes } from '@/components/tender-hands/data';
import { api, type DashboardSummary, type Donation, type RecurringDonation, type User } from '@/lib/api';

export const Route = createFileRoute('/dashboard')({
  head: () => ({
    meta: [
      { title: 'Donor Dashboard | Tender Hands' },
      { name: 'description', content: 'Your giving space. Track donations, manage recurring gifts.' },
      { property: 'og:title', content: 'Donor Dashboard | Tender Hands' },
      { property: 'og:description', content: 'Your generosity, your community, your impact.' },
      { property: 'og:type', content: 'website' },
      { name: 'twitter:card', content: 'summary_large_image' },
    ],
  }),
  component: Dashboard,
});

function receiptBlob(charity: string, amount: number, date: string, mpesaReceipt?: string | null) {
  const url = URL.createObjectURL(
    new Blob(
      [`TENDER HANDS — RECEIPT\n\nCharity: ${charity}\nAmount: ${kes(amount)}\nDate: ${date}\n${mpesaReceipt ? `M-Pesa Receipt: ${mpesaReceipt}\n` : ''}\n`],
      { type: 'text/plain' },
    ),
  );
  const a = document.createElement('a');
  a.href = url;
  a.download = 'tender-hands-receipt.txt';
  a.click();
  URL.revokeObjectURL(url);
}

function Dashboard() {
  const navigate = useNavigate();
  const { donate } = useGiving();

  const [user, setUser] = useState<User | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [donations, setDonations] = useState<Donation[]>([]);
  const [recurring, setRecurring] = useState<RecurringDonation[]>([]);
  const [loading, setLoading] = useState(true);
  const [authChecked, setAuthChecked] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    setIsLoggedIn(api.auth.isLoggedIn());
    setAuthChecked(true);
  }, []);

  useEffect(() => {
    if (!authChecked) return;

    if (!isLoggedIn) {
      setLoading(false);
      return;
    }

    Promise.all([
      api.auth.me(),
      api.dashboard.summary(),
      api.donations.myHistory(),
      api.recurring.list(),
    ])
      .then(([u, s, d, r]) => {
        // Admins have their own dashboard
        if (u.role === 'admin') {
          navigate({ to: '/admin' });
          return;
        }
        setUser(u);
        setSummary(s);
        setDonations(d);
        setRecurring(r);
      })
      .catch(() => {
        // Token expired or invalid — send to login
        api.auth.logout();
        navigate({ to: '/account' });
      })
      .finally(() => setLoading(false));
  }, [authChecked, isLoggedIn]);

  const handleLogout = () => {
    api.auth.logout();
    navigate({ to: '/' });
  };

  // ── Not logged in ──
  if (authChecked && !isLoggedIn && !loading) {
    return (
      <div className="min-h-screen bg-secondary flex items-center justify-center px-4">
        <div className="bg-card border border-border rounded-lg p-10 max-w-sm w-full text-center">
          <span className="icon-tile mx-auto mb-4"><HandHeart size={22} /></span>
          <h1 className="text-xl font-semibold mb-2">Your giving space awaits.</h1>
          <p className="section-copy mb-6">Log in to see your donations, receipts, and recurring gifts.</p>
          <Button asChild className="w-full h-11">
            <Link to="/account">Log in or create account</Link>
          </Button>
          <Button asChild variant="ghost" className="w-full mt-2">
            <Link to="/charities">Explore charities</Link>
          </Button>
        </div>
      </div>
    );
  }

  // ── Loading ──
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="animate-spin text-primary" size={32} />
      </div>
    );
  }

  // ── Logged-in donor view ──
  const displayName = user?.full_name?.split(' ')[0] ?? 'there';
  const initials = user?.full_name?.split(' ').map(w => w[0]).slice(0, 2).join('') ?? '?';

  return (
    <div className="dashboard-layout">
      <aside className="dashboard-sidebar flex flex-col">
        <Brand />
        <p className="text-[9px] text-muted-foreground uppercase tracking-widest mt-9 mb-4 hidden sm:block">
          Your giving space
        </p>
        <nav className="flex flex-wrap sm:flex-col gap-2 mt-2" aria-label="Dashboard navigation">
          <Button variant="secondary" asChild className="justify-start">
            <Link to="/dashboard"><LayoutDashboard size={15} /> Dashboard</Link>
          </Button>
          <Button variant="ghost" asChild className="justify-start">
            <a href="#history"><ReceiptText size={15} /> Donation History</a>
          </Button>
          <Button variant="ghost" asChild className="justify-start">
            <Link to="/charities"><Search size={15} /> Find Charities</Link>
          </Button>
          <Button variant="ghost" asChild className="justify-start">
            <a href="#recurring"><Repeat size={15} /> Recurring</a>
          </Button>
        </nav>
        <div className="mt-auto pt-8">
          <Button variant="ghost" className="justify-start w-full" onClick={handleLogout}>
            <LogOut size={15} /> Log out
          </Button>
        </div>
      </aside>

      <main className="dashboard-main">
        {/* Top bar */}
        <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-8">
          <span>My Giving / Dashboard</span>
          <span className="flex gap-2 items-center">
            <span className="bg-accent text-primary rounded-full w-7 h-7 grid place-items-center font-semibold text-xs">
              {initials}
            </span>
            {user?.full_name} · {user?.role}
          </span>
        </div>

        {/* Header */}
        <div className="flex justify-between gap-4 items-center mb-6">
          <div>
            <h1 className="text-[29px]">Good morning, {displayName}.</h1>
            <p className="section-copy mt-2">Here's the good your generosity is creating.</p>
          </div>
          <Button onClick={() => donate()} className="text-xs">
            Make a Donation <Heart size={14} />
          </Button>
        </div>

        {/* Summary cards */}
        <div className="grid sm:grid-cols-3 gap-4 mb-5">
          {[
            [kes(summary?.total_donated ?? 0), 'Total donated', 'Every gift makes a difference'],
            [String(summary?.charities_supported ?? 0), 'Charities supported', 'Communities, countless possibilities'],
            [kes(summary?.monthly_giving ?? 0), 'Monthly giving', 'Your kindness, on repeat'],
          ].map(([value, label, copy]) => (
            <article className="bg-card border border-border rounded-md p-5" key={label}>
              <p className="text-xs text-muted-foreground flex justify-between">
                {label}<Heart size={14} className="text-primary" />
              </p>
              <p className="text-2xl font-semibold mt-3 mb-2">{value}</p>
              <p className="text-[10px] text-muted-foreground">{copy}</p>
            </article>
          ))}
        </div>

        {/* Donation history */}
        <section id="history" className="bg-card border border-border rounded-md overflow-hidden mb-8">
          <div className="flex justify-between items-center p-5">
            <h2 className="text-lg">Your donation history</h2>
            <span className="text-[10px] text-muted-foreground">{donations.length} gifts</span>
          </div>
          {donations.length === 0 ? (
            <p className="text-xs text-muted-foreground p-5">
              No donations yet.{' '}
              <Link to="/charities" className="text-primary">Find a cause →</Link>
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="donation-table">
                <thead>
                  <tr>
                    {['Charity', 'Amount', 'Date', 'Method', 'Status', 'Receipt'].map(h => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {donations.map(d => (
                    <tr key={d.id}>
                      <td>
                        <span className="flex gap-2 items-center">
                          <HandHeart size={14} className="text-primary" />
                          {d.charity_name}
                        </span>
                      </td>
                      <td className="font-medium">{kes(d.amount)}</td>
                      <td className="text-muted-foreground">
                        {new Date(d.created_at).toLocaleDateString('en-GB', {
                          day: '2-digit', month: 'short', year: 'numeric',
                        })}
                      </td>
                      <td className="text-muted-foreground">{d.payment_method}</td>
                      <td>
                        <span className={`text-[10px] px-2 py-1 rounded ${
                          d.status === 'completed'
                            ? 'text-primary bg-secondary'
                            : d.status === 'failed'
                              ? 'text-destructive bg-destructive/10'
                              : 'text-muted-foreground bg-muted'
                        }`}>
                          {d.status}
                        </span>
                      </td>
                      <td>
                        {d.status === 'completed' && (
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={`Download receipt for ${d.charity_name}`}
                            onClick={() => receiptBlob(d.charity_name, d.amount, d.created_at, d.mpesa_receipt)}
                          >
                            <Download size={14} className="text-primary" />
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Recurring donations */}
        <section id="recurring" className="mt-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl">Kindness, on repeat.</h2>
          </div>
          {recurring.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No recurring donations yet.{' '}
              <Link to="/charities" className="text-primary">Set one up →</Link>
            </p>
          ) : (
            <div className="grid md:grid-cols-2 gap-4">
              {recurring.map(r => (
                <article key={r.id} className="bg-card border border-border rounded-md p-5">
                  <div className="flex justify-between">
                    <h3 className="text-sm font-semibold">{r.charity_name}</h3>
                    <span className={`text-[10px] px-2 py-1 rounded ${
                      r.status === 'active' ? 'text-primary bg-secondary' : 'text-muted-foreground bg-muted'
                    }`}>
                      {r.status}
                    </span>
                  </div>
                  <p className="text-xl font-semibold mt-4">
                    {kes(r.amount)}{' '}
                    <span className="text-[10px] text-muted-foreground font-normal">/ {r.frequency}</span>
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-1">
                    Next gift ·{' '}
                    {new Date(r.next_run_date).toLocaleDateString('en-GB', {
                      day: '2-digit', month: 'short', year: 'numeric',
                    })}
                  </p>
                  <div className="border-t border-border mt-4 pt-3 flex justify-between items-center">
                    <span className="text-[10px] text-primary flex gap-1">
                      <BadgeCheck size={12} /> Verified charity
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        api.recurring
                          .update(r.id, { status: 'cancelled' })
                          .then(() => setRecurring(prev => prev.filter(x => x.id !== r.id)))
                      }
                    >
                      Cancel <ArrowUpRight size={13} />
                    </Button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <p className="text-[10px] text-muted-foreground mt-10">
          © 2026 Tender Hands · A little kindness goes a long way.
        </p>
      </main>
    </div>
  );
}
