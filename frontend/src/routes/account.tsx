import { useState } from 'react';
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { ArrowRight, Eye, EyeOff, HandHeart, LockKeyhole, ShieldCheck, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Brand } from '@/components/tender-hands/shared';
import { api, ApiError } from '@/lib/api';

export const Route = createFileRoute('/account')({
  head: () => ({
    meta: [
      { title: 'Your kindness belongs here | Tender Hands' },
      { name: 'description', content: 'Explore the Tender Hands account experience and donor community.' },
      { property: 'og:title', content: 'Your kindness belongs here | Tender Hands' },
      { property: 'og:description', content: 'One account. Meaningful connections. A lasting difference.' },
      { property: 'og:type', content: 'website' },
      { name: 'twitter:card', content: 'summary_large_image' },
    ],
  }),
  component: Account,
});

function Password({ id, value, onChange, placeholder = 'Enter your password', disabled = false }: {
  id: string;
  value?: string;
  onChange?: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
}) {
  const [show, setShow] = useState(false);
  return (
    <label>
      Password
      <div className="relative">
        <input
          id={id}
          type={show ? 'text' : 'password'}
          placeholder={placeholder}
          disabled={disabled}
          value={value}
          onChange={e => onChange?.(e.target.value)}
          aria-label="Password"
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label={show ? 'Hide password' : 'Show password'}
          onClick={() => setShow(!show)}
          className="absolute right-1 top-1"
        >
          {show ? <EyeOff size={15} /> : <Eye size={15} />}
        </Button>
      </div>
    </label>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="flex gap-2 items-start bg-destructive/10 text-destructive text-xs p-3 rounded">
      <AlertCircle size={14} className="mt-0.5 shrink-0" />
      {message}
    </div>
  );
}

function Account() {
  const navigate = useNavigate();

  // Login form state
  const [loginId, setLoginId] = useState('');
  const [loginPw, setLoginPw] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState('');

  // Register form state
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regPw, setRegPw] = useState('');
  const [regLoading, setRegLoading] = useState(false);
  const [regError, setRegError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError('');
    try {
      await api.auth.login(loginId, loginPw);
      navigate({ to: '/dashboard' });
    } catch (err) {
      setLoginError(err instanceof ApiError ? err.message : 'Login failed. Please try again.');
    } finally {
      setLoginLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegLoading(true);
    setRegError('');
    try {
      await api.auth.register({
        full_name: regName,
        email: regEmail,
        ...(regPhone ? { phone: regPhone } : {}),
        password: regPw,
        role: 'donor',
      });
      navigate({ to: '/dashboard' });
    } catch (err) {
      if (err instanceof ApiError && err.errors) {
        const first = Object.values(err.errors).flat()[0];
        setRegError(first ?? err.message);
      } else {
        setRegError(err instanceof Error ? err.message : 'Registration failed. Please try again.');
      }
    } finally {
      setRegLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-secondary py-10 px-5">
      <div className="max-w-[940px] mx-auto">
        <div className="bg-card border border-border rounded-lg p-7 md:p-12">
          <div className="text-center border-b border-border pb-7">
            <Brand />
            <h1 className="section-title mt-4">Your kindness belongs here.</h1>
            <p className="section-copy mt-2">One account. Meaningful connections. A lasting difference.</p>
          </div>

          <div className="account-grid">
            {/* ── Login ── */}
            <section>
              <h2 className="text-2xl">Welcome back</h2>
              <p className="section-copy mt-1 mb-5">Log in to continue the good you started.</p>

              <form className="grid gap-4" onSubmit={handleLogin}>
                {loginError && <ErrorBox message={loginError} />}
                <label>
                  Email or phone number
                  <input
                    type="text"
                    placeholder="njeri.wanjiku@gmail.com or +254712345678"
                    value={loginId}
                    onChange={e => setLoginId(e.target.value)}
                    required
                  />
                </label>
                <Password id="login-password" value={loginPw} onChange={setLoginPw} />
                <Button type="submit" className="h-11" disabled={loginLoading}>
                  {loginLoading ? <Loader2 className="animate-spin" size={16} /> : <>Log in <ArrowRight /></>}
                </Button>
                <p className="text-[11px] text-center text-muted-foreground">
                  New to Tender Hands?{' '}
                  <a href="#create-account" className="text-primary">Create Account →</a>
                </p>
              </form>

              <div className="bg-secondary p-5 mt-6 rounded">
                <HandHeart size={22} className="text-primary mb-3" />
                <h3 className="text-lg">A good heart. A trusted home.</h3>
                <p className="section-copy mt-2">
                  Keep your receipts in one place, follow the charities you love and make giving a part of everyday life.
                </p>
                <p className="text-[10px] text-primary mt-3 font-bold">M-PESA</p>
              </div>
            </section>

            {/* ── Register ── */}
            <section id="create-account">
              <h2 className="text-2xl">Create an account</h2>
              <p className="section-copy mt-1 mb-5">Join a community turning kindness into action.</p>

              <form className="grid gap-4" onSubmit={handleRegister}>
                {regError && <ErrorBox message={regError} />}
                <label>
                  Full name
                  <input placeholder="Njeri Wanjiku" value={regName} onChange={e => setRegName(e.target.value)} required />
                </label>
                <label>
                  Email address
                  <input type="email" placeholder="njeri.wanjiku@gmail.com" value={regEmail} onChange={e => setRegEmail(e.target.value)} required />
                </label>
                <label>
                  Kenyan phone number <span className="text-muted-foreground text-[10px]">(optional)</span>
                  <input placeholder="+254 712 345 678" value={regPhone} onChange={e => setRegPhone(e.target.value)} />
                </label>
                <Password id="register-password" value={regPw} onChange={setRegPw} placeholder="At least 8 chars, a number and symbol" />
                <p className="text-[10px] text-muted-foreground -mt-2">
                  At least 8 characters, with a number and a symbol.
                </p>
                <label className="flex items-center gap-2 text-[11px]">
                  <input type="checkbox" required />
                  I agree to the Terms of Use and Privacy Policy.
                </label>
                <Button type="submit" className="h-11" disabled={regLoading}>
                  {regLoading ? <Loader2 className="animate-spin" size={16} /> : 'Create Account'}
                </Button>
                <p className="flex justify-center gap-1.5 text-[10px] text-muted-foreground">
                  <LockKeyhole size={12} /> Your details are private. Your impact is powerful.
                </p>
              </form>
            </section>
          </div>
        </div>

        <div className="flex justify-between flex-wrap gap-3 mt-6 text-[10px] text-muted-foreground">
          <Link to="/">© 2026 Tender Hands · Made for a kinder Kenya</Link>
          <span className="flex gap-2 items-center">
            <ShieldCheck size={13} className="text-primary" /> Verified charities. Secure M-Pesa giving.
          </span>
        </div>
      </div>
    </main>
  );
}
