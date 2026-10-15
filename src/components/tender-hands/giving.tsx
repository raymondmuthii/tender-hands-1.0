import { createContext, useContext, useState, type ReactNode } from 'react';
import { Link } from '@tanstack/react-router';
import { Heart, LockKeyhole, CheckCircle2, Smartphone } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { charities, kes, startingDonations, type Charity } from './data';

type GivingContext = { donate: (charity?: Charity) => void; donations: typeof startingDonations };
const Giving = createContext<GivingContext>({ donate: () => {}, donations: startingDonations });
export const useGiving = () => useContext(Giving);
export function GivingProvider({ children }: { children: ReactNode }) {
 const [selected, setSelected] = useState<Charity | null>(null);
 const [amount, setAmount] = useState('1000');
 const [done, setDone] = useState(false);
 const [donations, setDonations] = useState(startingDonations);
 const donate = (charity = charities[0]) => { if (!charity) return; setSelected(charity); setAmount('1000'); setDone(false); };
 return <Giving.Provider value={{ donate, donations }}>{children}
  <Dialog open={!!selected} onOpenChange={open => { if (!open) setSelected(null); }}>
   <DialogContent className="rounded-lg max-w-[calc(100%-32px)] sm:max-w-md p-8">
    {done ? <><div className="icon-tile mx-auto"><CheckCircle2 size={24}/></div><DialogTitle className="text-center font-display text-2xl">A little kindness. A real possibility.</DialogTitle><DialogDescription className="text-center">Your {kes(Number(amount))} demonstration gift to {selected?.name} has been added to your sample donation history. No money was collected.</DialogDescription><Button asChild onClick={() => setSelected(null)}><Link to="/dashboard">View donation history <Heart size={16}/></Link></Button></> : <>
    <div className="icon-tile"><Heart size={22}/></div><DialogTitle className="font-display text-2xl">Give to {selected?.name}</DialogTitle><DialogDescription>This is a demonstration. No M-Pesa request will be sent and no money will be collected.</DialogDescription>
    <form className="grid gap-5" onSubmit={e => { e.preventDefault(); if (!selected || Number(amount) <= 0) return; setDonations([{ charity: selected.name, amount: Number(amount), date: new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) }, ...donations]); setDone(true); }}>
     <label>Donation amount (KES)<input type="number" required min="1" step="1" value={amount} onChange={e => setAmount(e.target.value)}/></label>
     <div className="flex gap-2">{[500,1000,2500].map(n => <Button type="button" key={n} variant={amount === String(n) ? 'default' : 'outline'} className="flex-1" onClick={() => setAmount(String(n))}>{kes(n)}</Button>)}</div>
     <Button type="submit" className="h-11"><Smartphone size={16}/> Preview donation</Button>
     <p className="text-xs text-muted-foreground text-center flex justify-center items-center gap-2"><LockKeyhole size={12}/> Demonstration only · No payment required</p>
    </form></>}
   </DialogContent>
  </Dialog>
 </Giving.Provider>;
}
