import education from '@/assets/education.jpg';
import water from '@/assets/water.jpg';
import healthcare from '@/assets/healthcare.jpg';
import garden from '@/assets/community-garden.jpg';
export const charities = [
  { id: 'amani', name: 'Amani Learning Trust', category: 'Education', location: 'Kilifi, Nairobi', description: 'Open doors to learning with books, meals and safe classrooms.', amount: 420000, goal: 500000, image: education },
  { id: 'maji', name: 'Maji Kwa Wote', category: 'Clean water', location: 'Kilifi County', description: 'Bring safe, reliable water closer to families in rural Kilifi.', amount: 680000, goal: 1000000, image: water },
  { id: 'tumaini', name: 'Tumaini Health Collective', category: 'Healthcare', location: 'Mombasa County', description: 'Help community clinics deliver care where it is needed most.', amount: 310000, goal: 500000, image: healthcare },
  { id: 'tupande', name: 'Tupande Community', category: 'Livelihoods', location: 'Kisumu County', description: 'Grow food security and opportunity through community gardens.', amount: 192000, goal: 300000, image: garden },
];
export type Charity = typeof charities[number];
export const kes = (amount: number) => `KES ${amount.toLocaleString('en-KE')}`;
export const startingDonations = [
 { charity: 'Amani Learning Trust', amount: 7000, date: '08 Oct 2026' },
 { charity: 'Tupande Community', amount: 1500, date: '20 Sep 2026' },
 { charity: 'Amani Learning Trust', amount: 2500, date: '10 Sep 2026' },
 { charity: 'Maji Kwa Wote', amount: 5000, date: '20 Aug 2026' },
 { charity: 'Tumaini Health Collective', amount: 2500, date: '10 Aug 2026' },
];
