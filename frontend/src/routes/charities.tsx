import { useState, useEffect } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import { Search, SlidersHorizontal, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Header, Footer, CharityCard } from '@/components/tender-hands/shared';
import { charities as fallbackCharities, localImages } from '@/components/tender-hands/data';
import { api, type Charity as ApiCharity } from '@/lib/api';

export const Route = createFileRoute('/charities')({
  head: () => ({
    meta: [
      { title: 'Explore Charities | Tender Hands' },
      { name: 'description', content: 'Find a Kenyan charity close to your heart. Explore education, water, healthcare and livelihoods.' },
      { property: 'og:title', content: 'Explore Charities | Tender Hands' },
      { property: 'og:description', content: 'Local roots. Lasting change. Discover Kenyan community causes.' },
      { property: 'og:type', content: 'website' },
      { name: 'twitter:card', content: 'summary_large_image' },
    ],
  }),
  component: Charities,
});

/** Normalise an API charity into the shape CharityCard expects. */
function toCardShape(c: ApiCharity) {
  return {
    id: c.id,                                     // slug
    name: c.name,
    category: c.category,
    location: c.location,
    description: c.description,
    amount: c.amount,
    goal: c.goal,
    // Use the remote image_url if available, otherwise fall back to local asset
    image: c.image ?? localImages[c.id] ?? localImages['amani'] ?? '',
  };
}

function Charities() {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All causes');
  const [charities, setCharities] = useState(fallbackCharities);
  const [loading, setLoading] = useState(true);

  // Fetch live data from the backend
  useEffect(() => {
    api.charities
      .list()
      .then(({ data }) => setCharities(data.map(toCardShape)))
      .catch(() => {
        // Backend unavailable — keep the local fallback data shown above
      })
      .finally(() => setLoading(false));
  }, []);

  const categories = ['All causes', ...Array.from(new Set(charities.map((c) => c.category)))];

  const results = charities.filter(
    (c) =>
      (category === 'All causes' || c.category === category) &&
      `${c.name} ${c.location} ${c.description}`.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <>
      <Header />
      <main>
        <section className="bg-secondary py-12">
          <div className="site-container">
            <p className="eyebrow">Local roots. Lasting change.</p>
            <h1 className="section-title mt-4">Find a cause close to your heart.</h1>
            <p className="section-copy mt-3">Every organisation is verified by our team. Every act of kindness matters.</p>
          </div>
        </section>

        <section className="site-container py-10 min-h-[600px]">
          <div className="flex flex-wrap gap-5 items-center justify-between mb-6">
            <div className="flex gap-2 flex-wrap">
              {categories.map((c) => (
                <Button
                  key={c}
                  variant={c === category ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setCategory(c)}
                >
                  {c === 'All causes' && <SlidersHorizontal size={13} />} {c}
                </Button>
              ))}
            </div>
            <label className="relative w-full sm:w-64">
              <span className="sr-only">Search charities</span>
              <input
                placeholder="Search charities or places"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <Search className="absolute right-3 top-3 text-muted-foreground" size={16} />
            </label>
          </div>

          {loading ? (
            <div className="flex justify-center py-20">
              <Loader2 className="animate-spin text-primary" size={32} />
            </div>
          ) : (
            <>
              <p className="text-xs text-muted-foreground mb-6">
                {results.length} {results.length === 1 ? 'charity' : 'charities'} making a difference
              </p>
              <div className="charity-grid">
                {results.map((c) => (
                  <CharityCard key={c.id} charity={c} />
                ))}
              </div>

              {results.length === 0 && (
                <div className="text-center py-20">
                  <Search size={30} className="mx-auto text-primary mb-4" />
                  <h2 className="text-xl">No charities found</h2>
                  <p className="section-copy my-3">Try a different name or place.</p>
                  <Button
                    variant="outline"
                    onClick={() => { setSearch(''); setCategory('All causes'); }}
                  >
                    Clear filters
                  </Button>
                </div>
              )}
            </>
          )}
        </section>
      </main>
      <Footer />
    </>
  );
}
