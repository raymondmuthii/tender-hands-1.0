import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { Link } from '@tanstack/react-router';
import { Heart, LockKeyhole, CheckCircle2, Smartphone, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { charities as fallbackCharities, kes, type Charity } from './data';
import { api } from '@/lib/api';

type GivingContext = {
  donate: (charity?: Charity) => void;
};

const Giving = createContext<GivingContext>({ donate: () => {} });
export const useGiving = () => useContext(Giving);

export function GivingProvider({ children }: { children: ReactNode }) {
  const [selected, setSelected] = useState<Charity | null>(null);
  const [amount, setAmount] = useState('1000');
  const [phone, setPhone] = useState('');
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const [isLoggedIn, setIsLoggedIn] = useState(false);
  // Read auth state only on the client (localStorage not available during SSR)
  useEffect(() => {
    setIsLoggedIn(api.auth.isLoggedIn());
  }, []);

  const donate = (charity = fallbackCharities[0]) => {
    if (!charity) return;
    setSelected(charity);
    setAmount('1000');
    setPhone('');
    setDone(false);
    setErrorMsg('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected || Number(amount) <= 0) return;

    setSubmitting(true);
    setErrorMsg('');

    try {
      await api.donations.create({
        charity_id: selected.id,
        amount: Number(amount),
        phone,
      });
      setDone(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Something went wrong. Please try again.';
      setErrorMsg(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Giving.Provider value={{ donate }}>
      {children}

      <Dialog open={!!selected} onOpenChange={open => { if (!open) setSelected(null); }}>
        <DialogContent className="rounded-lg max-w-[calc(100%-32px)] sm:max-w-md p-8">
          {done ? (
            <>
              <div className="icon-tile mx-auto"><CheckCircle2 size={24} /></div>
              <DialogTitle className="text-center font-display text-2xl">
                Check your phone for the M-Pesa prompt.
              </DialogTitle>
              <DialogDescription className="text-center">
                Your KES {Number(amount).toLocaleString('en-KE')} donation to {selected?.name} is
                being processed. Enter your M-Pesa PIN to complete the payment.
              </DialogDescription>
              <Button asChild onClick={() => setSelected(null)}>
                <Link to="/dashboard">View donation history <Heart size={16} /></Link>
              </Button>
            </>
          ) : !isLoggedIn ? (
            /* ── Not logged in — prompt to sign in ── */
            <>
              <div className="icon-tile"><Heart size={22} /></div>
              <DialogTitle className="font-display text-2xl">Give to {selected?.name}</DialogTitle>
              <DialogDescription>
                Create a free account or log in to donate securely via M-Pesa.
              </DialogDescription>
              <div className="grid gap-3 mt-2">
                <Button asChild className="h-11" onClick={() => setSelected(null)}>
                  <Link to="/account">Log in or create account</Link>
                </Button>
                <p className="text-xs text-muted-foreground text-center flex justify-center items-center gap-2">
                  <LockKeyhole size={12} /> Secure payments via M-Pesa
                </p>
              </div>
            </>
          ) : (
            /* ── Logged in — real donation form ── */
            <>
              <div className="icon-tile"><Heart size={22} /></div>
              <DialogTitle className="font-display text-2xl">Give to {selected?.name}</DialogTitle>
              <DialogDescription>
                An M-Pesa STK push will be sent to your phone to complete the payment.
              </DialogDescription>

              {errorMsg && (
                <div className="flex gap-2 items-start bg-destructive/10 text-destructive text-xs p-3 rounded">
                  <AlertCircle size={14} className="mt-0.5 shrink-0" />
                  {errorMsg}
                </div>
              )}

              <form className="grid gap-5" onSubmit={handleSubmit}>
                <label>
                  Donation amount (KES)
                  <input
                    type="number"
                    required
                    min="10"
                    step="1"
                    value={amount}
                    onChange={e => setAmount(e.target.value)}
                  />
                </label>
                <div className="flex gap-2">
                  {[500, 1000, 2500].map(n => (
                    <Button
                      type="button"
                      key={n}
                      variant={amount === String(n) ? 'default' : 'outline'}
                      className="flex-1"
                      onClick={() => setAmount(String(n))}
                    >
                      {kes(n)}
                    </Button>
                  ))}
                </div>
                <label>
                  M-Pesa phone number
                  <input
                    type="tel"
                    required
                    placeholder="+254 7XX XXX XXX"
                    value={phone}
                    onChange={e => setPhone(e.target.value)}
                  />
                </label>
                <Button type="submit" className="h-11" disabled={submitting}>
                  {submitting
                    ? 'Sending…'
                    : <><Smartphone size={16} /> Send M-Pesa request</>}
                </Button>
              </form>
            </>
          )}
        </DialogContent>
      </Dialog>
    </Giving.Provider>
  );
}
