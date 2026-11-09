/**
 * data.ts
 *
 * Static assets (images) and utility helpers.
 * Live charity data now comes from the backend via src/lib/api.ts.
 *
 * The `charities` array below is kept as a LOCAL FALLBACK only —
 * used when the API is unavailable (e.g. no internet, backend not running).
 */
import education from '@/assets/education.jpg';
import water from '@/assets/water.jpg';
import healthcare from '@/assets/healthcare.jpg';
import garden from '@/assets/community-garden.jpg';

export const charities = [
  { id: 'amani', name: 'Amani Learning Trust', category: 'Education', location: 'Kilifi, Nairobi', description: 'Open doors to learning with books, meals and safe classrooms.', amount: 420000, goal: 500000, image: education },
  { id: 'maji-kwa-wote', name: 'Maji Kwa Wote', category: 'Clean water', location: 'Kilifi County', description: 'Bring safe, reliable water closer to families in rural Kilifi.', amount: 680000, goal: 1000000, image: water },
  { id: 'tumaini-health', name: 'Tumaini Health Collective', category: 'Healthcare', location: 'Mombasa County', description: 'Help community clinics deliver care where it is needed most.', amount: 310000, goal: 500000, image: healthcare },
  { id: 'tupande', name: 'Tupande Community', category: 'Livelihoods', location: 'Kisumu County', description: 'Grow food security and opportunity through community gardens.', amount: 192000, goal: 300000, image: garden },
];

export type Charity = typeof charities[number];

export const kes = (amount: number) => `KES ${amount.toLocaleString('en-KE')}`;

/** Local image map — used to display images returned by the API. */
export const localImages: Record<string, string> = {
  amani: education,
  'maji-kwa-wote': water,
  'tumaini-health': healthcare,
  tupande: garden,
};
