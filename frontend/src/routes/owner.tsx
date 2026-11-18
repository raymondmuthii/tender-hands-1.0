import { useCallback, useEffect, useMemo, useState } from 'react';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import {
  AlertCircle, BadgeCheck, Clock, Loader2, LogOut, Pencil, Plus,
  RefreshCw, Trash2, XCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Brand } from '@/components/tender-hands/shared';
import {
  api,
  ApiError,
  type Beneficiary,
  type ImpactStory,
  type InventoryItem,
  type MyCharity,
  type User,
} from '@/lib/api';
import { routeForRole } from '@/lib/roles';

export const Route = createFileRoute('/owner')({
  head: () => ({
    meta: [
      { title: 'Charity Dashboard | Tender Hands' },
      {
        name: 'description',
        content: 'Manage your charity application, impact stories, beneficiaries and inventory.',
      },
      { name: 'robots', content: 'noindex' },
    ],
  }),
  component: OwnerDashboard,
});

// ── Helpers ────────────────────────────────────────────────────────────────

function messageOf(err: unknown, fallback: string) {
  if (err instanceof ApiError) {
    const first = err.errors ? Object.values(err.errors).flat()[0] : undefined;
    return first ?? err.message;
  }
  return err instanceof Error ? err.message : fallback;
}

function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80);
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; className: string; icon: React.ReactNode }> = {
    pending: {
      label: 'Pending review',
      className: 'text-primary bg-secondary',
      icon: <Clock size={12} />,
    },
    approved: {
      label: 'Approved',
      className: 'text-primary bg-secondary',
      icon: <BadgeCheck size={12} />,
    },
    rejected: {
      label: 'Rejected',
      className: 'text-destructive bg-destructive/10',
      icon: <XCircle size={12} />,
    },
  };
  const badge = map[status] ?? map['pending'];
  if (!badge) return null;
  return (
    <span className={`inline-flex items-center gap-1.5 text-[10px] px-2 py-1 rounded ${badge.className}`}>
      {badge.icon}
      {badge.label}
    </span>
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

// ── Route guard ────────────────────────────────────────────────────────────

function OwnerDashboard() {
  const navigate = useNavigate();
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (!api.auth.isLoggedIn()) {
      setReady(true);
      navigate({ to: '/account' });
      return;
    }

    api.auth
      .me()
      .then(me => {
        if (me.role !== 'charity') {
          navigate({ to: routeForRole(me.role) });
          return;
        }
        setUser(me);
        setReady(true);
      })
      .catch(() => {
        api.auth.logout();
        navigate({ to: '/account' });
      });
  }, [navigate]);

  if (!ready || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="animate-spin text-primary" size={32} />
      </div>
    );
  }

  return <OwnerWorkspace user={user} />;
}

// ── Owner workspace ────────────────────────────────────────────────────────

type Tab = 'stories' | 'beneficiaries' | 'inventory';

function OwnerWorkspace({ user }: { user: User }) {
  const navigate = useNavigate();
  const [charity, setCharity] = useState<MyCharity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<Tab>('stories');

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    api.charities
      .mine()
      .then(setCharity)
      .catch(e => setError(messageOf(e, 'Could not load your charity.')))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  const slug = charity?.slug ?? '';

  const storyClient = useMemo<CrudApi<ImpactStory>>(
    () => ({
      list: () => api.charities.stories(slug, { all: true }),
      create: values =>
        api.charities.createStory(slug, {
          title: String(values['title'] ?? ''),
          content: String(values['content'] ?? ''),
          image_url: String(values['image_url'] ?? '') || null,
          published: Boolean(values['published']),
        }),
      update: (id, values) =>
        api.charities.updateStory(slug, id, {
          title: String(values['title'] ?? ''),
          content: String(values['content'] ?? ''),
          image_url: String(values['image_url'] ?? '') || null,
          published: Boolean(values['published']),
        }),
      remove: id => api.charities.deleteStory(slug, id),
    }),
    [slug],
  );

  const beneficiaryClient = useMemo<CrudApi<Beneficiary>>(
    () => ({
      list: () => api.charities.beneficiaries(slug),
      create: values =>
        api.charities.createBeneficiary(slug, {
          name: String(values['name'] ?? ''),
          age: values['age'] ? Number(values['age']) : null,
          location: String(values['location'] ?? '') || null,
          story: String(values['story'] ?? '') || null,
        }),
      update: (id, values) =>
        api.charities.updateBeneficiary(slug, id, {
          name: String(values['name'] ?? ''),
          age: values['age'] ? Number(values['age']) : null,
          location: String(values['location'] ?? '') || null,
          story: String(values['story'] ?? '') || null,
        }),
      remove: id => api.charities.deleteBeneficiary(slug, id),
    }),
    [slug],
  );

  const inventoryClient = useMemo<CrudApi<InventoryItem>>(
    () => ({
      list: () => api.charities.inventory(slug),
      create: values =>
        api.charities.createInventoryItem(slug, {
          name: String(values['name'] ?? ''),
          quantity: Number(values['quantity'] ?? 0),
          unit: String(values['unit'] ?? '') || null,
          notes: String(values['notes'] ?? '') || null,
        }),
      update: (id, values) =>
        api.charities.updateInventoryItem(slug, id, {
          name: String(values['name'] ?? ''),
          quantity: Number(values['quantity'] ?? 0),
          unit: String(values['unit'] ?? '') || null,
          notes: String(values['notes'] ?? '') || null,
        }),
      remove: id => api.charities.deleteInventoryItem(slug, id),
    }),
    [slug],
  );

  const handleLogout = () => {
    api.auth.logout();
    navigate({ to: '/' });
  };

  return (
    <div className="dashboard-layout">
      <aside className="dashboard-sidebar flex flex-col">
        <Brand />
        <p className="text-[9px] text-muted-foreground uppercase tracking-widest mt-9 mb-4 hidden sm:block">
          Charity space
        </p>
        <nav className="flex flex-col gap-2 mt-2" aria-label="Owner navigation">
          <Button variant={tab === 'stories' ? 'secondary' : 'ghost'} className="justify-start" onClick={() => setTab('stories')}>
            Impact stories
          </Button>
          <Button variant={tab === 'beneficiaries' ? 'secondary' : 'ghost'} className="justify-start" onClick={() => setTab('beneficiaries')}>
            Beneficiaries
          </Button>
          <Button variant={tab === 'inventory' ? 'secondary' : 'ghost'} className="justify-start" onClick={() => setTab('inventory')}>
            Inventory
          </Button>
        </nav>
        <div className="mt-auto pt-8">
          <Button variant="ghost" className="justify-start w-full" onClick={handleLogout}>
            <LogOut size={15} /> Log out
          </Button>
        </div>
      </aside>

      <main className="dashboard-main">
        <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
          <div>
            <p className="eyebrow">Tender Hands</p>
            <h1 className="text-[29px] mt-1">Charity dashboard</h1>
            <p className="section-copy mt-2">Signed in as {user.full_name}.</p>
          </div>
          {charity && <StatusBadge status={charity.status} />}
        </div>

        {loading ? (
          <CenteredLoader />
        ) : error ? (
          <ErrorCard message={error} onRetry={load} />
        ) : !charity ? (
          <ApplicationForm onApplied={setCharity} />
        ) : (
          <>
            <section className="bg-card border border-border rounded-md p-5 mb-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg">{charity.name}</h2>
                  <p className="text-xs text-muted-foreground mt-1">
                    {charity.category} · {charity.location} · Goal KES {charity.goal.toLocaleString('en-KE')}
                  </p>
                </div>
                <span className="text-[10px] text-muted-foreground">/{charity.slug}</span>
              </div>
              {charity.status !== 'approved' && (
                <p className="flex items-start gap-2 text-xs text-muted-foreground mt-4">
                  <AlertCircle size={14} className="mt-0.5 shrink-0" />
                  {charity.status === 'pending'
                    ? 'An admin is reviewing your application. You can prepare content now – it becomes public once you are approved.'
                    : 'Your application was rejected. Update your details and contact hello@tenderhands.ke to request another review.'}
                </p>
              )}
            </section>

            {tab === 'stories' && (
              <CrudTab
                title="Impact stories"
                description="Share what your donors made possible."
                emptyLabel="No impact stories yet."
                client={storyClient}
                fields={[
                  { key: 'title', label: 'Title', required: true },
                  { key: 'content', label: 'Story', type: 'textarea', required: true },
                  { key: 'image_url', label: 'Image URL (optional)' },
                  { key: 'published', label: 'Published', type: 'checkbox' },
                ]}
                summary={item => (item.published ? 'Published' : 'Draft')}
              />
            )}

            {tab === 'beneficiaries' && (
              <CrudTab
                title="Beneficiaries"
                description="The people your programmes support."
                emptyLabel="No beneficiaries yet."
                client={beneficiaryClient}
                fields={[
                  { key: 'name', label: 'Name', required: true },
                  { key: 'age', label: 'Age', type: 'number' },
                  { key: 'location', label: 'Location' },
                  { key: 'story', label: 'Story', type: 'textarea' },
                ]}
                summary={item =>
                  [item.age ? `${item.age} years` : null, item.location].filter(Boolean).join(' · ')
                }
              />
            )}

            {tab === 'inventory' && (
              <CrudTab
                title="Inventory"
                description="Track the supplies you hold."
                emptyLabel="No inventory items yet."
                client={inventoryClient}
                fields={[
                  { key: 'name', label: 'Item', required: true },
                  { key: 'quantity', label: 'Quantity', type: 'number', required: true },
                  { key: 'unit', label: 'Unit (e.g. books, kg)' },
                  { key: 'notes', label: 'Notes', type: 'textarea' },
                ]}
                summary={item => `${item.quantity}${item.unit ? ` ${item.unit}` : ''}`}
              />
            )}
          </>
        )}
      </main>
    </div>
  );
}

// ── Charity application ────────────────────────────────────────────────────

const CATEGORIES = ['Education', 'Clean water', 'Healthcare', 'Livelihoods'];

function ApplicationForm({ onApplied }: { onApplied: (charity: MyCharity) => void }) {
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [category, setCategory] = useState(CATEGORIES[0] ?? 'Education');
  const [location, setLocation] = useState('');
  const [description, setDescription] = useState('');
  const [goal, setGoal] = useState('100000');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await api.charities.apply({
        name,
        slug: slug || slugify(name),
        category,
        location,
        description,
        goal_amount: Number(goal),
      });
      // Re-read the owner record so the badge and slug come from the API.
      const mine = await api.charities.mine();
      if (mine) onApplied(mine);
    } catch (err) {
      setError(messageOf(err, 'Could not submit your application.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="bg-card border border-border rounded-md p-6">
      <h2 className="text-xl">Apply to join Tender Hands</h2>
      <p className="section-copy mt-1 mb-5">
        Tell us about your organisation. An admin reviews every application before it appears publicly.
      </p>

      <form className="grid gap-4 max-w-xl" onSubmit={handleSubmit}>
        {error && (
          <div className="flex gap-2 items-start bg-destructive/10 text-destructive text-xs p-3 rounded">
            <AlertCircle size={14} className="mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        <label>
          Organisation name
          <input
            required
            minLength={3}
            value={name}
            onChange={e => {
              setName(e.target.value);
              if (!slug || slug === slugify(name)) setSlug(slugify(e.target.value));
            }}
          />
        </label>

        <label>
          Public URL slug
          <input required minLength={2} value={slug} onChange={e => setSlug(slugify(e.target.value))} />
        </label>

        <label>
          Category
          <select value={category} onChange={e => setCategory(e.target.value)}>
            {CATEGORIES.map(c => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>

        <label>
          Location
          <input required value={location} onChange={e => setLocation(e.target.value)} />
        </label>

        <label>
          What do you do?
          <textarea
            required
            minLength={10}
            rows={4}
            value={description}
            onChange={e => setDescription(e.target.value)}
          />
        </label>

        <label>
          Funding goal (KES)
          <input
            type="number"
            required
            min={1}
            step={1}
            value={goal}
            onChange={e => setGoal(e.target.value)}
          />
        </label>

        <Button type="submit" className="h-11" disabled={submitting}>
          {submitting ? <Loader2 className="animate-spin" size={16} /> : 'Submit application'}
        </Button>
      </form>
    </section>
  );
}

// ── Generic CRUD tab ───────────────────────────────────────────────────────

type FieldDef = {
  key: string;
  label: string;
  type?: 'text' | 'number' | 'textarea' | 'checkbox';
  required?: boolean;
};

type FormValues = Record<string, string | boolean>;

type CrudApi<T> = {
  list: () => Promise<T[]>;
  create: (values: FormValues) => Promise<T>;
  update: (id: number, values: FormValues) => Promise<T>;
  remove: (id: number) => Promise<void>;
};

function emptyValues(fields: FieldDef[]): FormValues {
  const values: FormValues = {};
  for (const field of fields) values[field.key] = field.type === 'checkbox' ? false : '';
  return values;
}

function CrudTab<T extends { id: number }>({
  title,
  description,
  emptyLabel,
  fields,
  client,
  summary,
}: {
  title: string;
  description: string;
  emptyLabel: string;
  fields: FieldDef[];
  client: CrudApi<T>;
  summary: (item: T) => string;
}) {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [values, setValues] = useState<FormValues>(() => emptyValues(fields));
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    client
      .list()
      .then(setItems)
      .catch(e => setError(messageOf(e, 'Could not load this list.')))
      .finally(() => setLoading(false));
  }, [client]);

  useEffect(load, [load]);

  const resetForm = () => {
    setValues(emptyValues(fields));
    setEditingId(null);
    setFormError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setFormError('');
    try {
      if (editingId === null) await client.create(values);
      else await client.update(editingId, values);
      resetForm();
      load();
    } catch (err) {
      setFormError(messageOf(err, 'Could not save this item.'));
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (item: T) => {
    const record = item as unknown as Record<string, unknown>;
    const next = emptyValues(fields);
    for (const field of fields) {
      const raw = record[field.key];
      next[field.key] =
        field.type === 'checkbox' ? Boolean(raw) : raw === null || raw === undefined ? '' : String(raw);
    }
    setValues(next);
    setEditingId(item.id);
    setFormError('');
  };

  const handleDelete = async (id: number) => {
    if (typeof window !== 'undefined' && !window.confirm('Delete this item? This cannot be undone.')) {
      return;
    }
    setDeletingId(id);
    try {
      await client.remove(id);
      if (editingId === id) resetForm();
      load();
    } catch (err) {
      setFormError(messageOf(err, 'Could not delete this item.'));
    } finally {
      setDeletingId(null);
    }
  };

  const setValue = (key: string, value: string | boolean) => {
    setValues(prev => ({ ...prev, [key]: value }));
  };

  const primaryKey = fields[0]?.key ?? '';

  return (
    <div className="grid lg:grid-cols-[minmax(0,1fr)_360px] gap-6 items-start">
      <section className="bg-card border border-border rounded-md overflow-hidden">
        <div className="flex justify-between items-center p-5">
          <div>
            <h2 className="text-lg">{title}</h2>
            <p className="text-[11px] text-muted-foreground mt-1">{description}</p>
          </div>
          <span className="text-[10px] text-muted-foreground">{items.length} total</span>
        </div>

        {loading ? (
          <CenteredLoader />
        ) : error ? (
          <ErrorCard message={error} onRetry={load} />
        ) : items.length === 0 ? (
          <p className="text-xs text-muted-foreground p-5">{emptyLabel}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="donation-table">
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Details</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => {
                  const record = item as unknown as Record<string, unknown>;
                  return (
                    <tr key={item.id}>
                      <td className="font-medium">{String(record[primaryKey] ?? '')}</td>
                      <td className="text-muted-foreground">{summary(item)}</td>
                      <td>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-[11px]"
                            onClick={() => startEdit(item)}
                          >
                            <Pencil size={12} /> Edit
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-[11px] text-destructive"
                            disabled={deletingId === item.id}
                            onClick={() => handleDelete(item.id)}
                          >
                            {deletingId === item.id ? (
                              <Loader2 size={12} className="animate-spin" />
                            ) : (
                              <Trash2 size={12} />
                            )}
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="bg-card border border-border rounded-md p-5">
        <h3 className="text-sm font-semibold mb-4">
          {editingId === null ? 'Add item' : 'Edit item'}
        </h3>

        {formError && (
          <div className="flex gap-2 items-start bg-destructive/10 text-destructive text-xs p-3 rounded mb-4">
            <AlertCircle size={14} className="mt-0.5 shrink-0" />
            {formError}
          </div>
        )}

        <form className="grid gap-3" onSubmit={handleSubmit}>
          {fields.map(field => {
            const value = values[field.key];
            if (field.type === 'checkbox') {
              return (
                <label key={field.key} className="flex items-center gap-2 text-[11px]">
                  <input
                    type="checkbox"
                    checked={Boolean(value)}
                    onChange={e => setValue(field.key, e.target.checked)}
                  />
                  {field.label}
                </label>
              );
            }
            return (
              <label key={field.key}>
                {field.label}
                {field.type === 'textarea' ? (
                  <textarea
                    rows={3}
                    required={field.required}
                    value={typeof value === 'string' ? value : ''}
                    onChange={e => setValue(field.key, e.target.value)}
                  />
                ) : (
                  <input
                    type={field.type === 'number' ? 'number' : 'text'}
                    required={field.required}
                    value={typeof value === 'string' ? value : ''}
                    onChange={e => setValue(field.key, e.target.value)}
                  />
                )}
              </label>
            );
          })}

          <div className="flex gap-2">
            <Button type="submit" className="flex-1" disabled={saving}>
              {saving ? <Loader2 className="animate-spin" size={14} /> : <Plus size={14} />}
              {editingId === null ? 'Add' : 'Save'}
            </Button>
            {editingId !== null && (
              <Button type="button" variant="outline" onClick={resetForm}>
                Cancel
              </Button>
            )}
          </div>
        </form>
      </section>
    </div>
  );
}
