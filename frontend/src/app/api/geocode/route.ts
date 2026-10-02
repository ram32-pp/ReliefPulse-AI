import { NextRequest, NextResponse } from 'next/server';

interface SearchResult {
  place_id: number;
  display_name: string;
  lat: string;
  lon: string;
}

// In-memory cache to respect Nominatim rate limit (1 req/sec) and prevent redundant calls
const cache = new Map<string, { timestamp: number; data: any }>();
const CACHE_TTL_MS = 10 * 60 * 1000; // 10 minutes

// Fallback emergency locations across Pakistan for resilience and offline support
const FALLBACK_LOCATIONS: SearchResult[] = [
  { place_id: 1001, display_name: 'Karachi, Sindh, Pakistan', lat: '24.8607', lon: '67.0011' },
  { place_id: 1002, display_name: 'Lahore, Punjab, Pakistan', lat: '31.5204', lon: '74.3587' },
  { place_id: 1003, display_name: 'Islamabad, Capital Territory, Pakistan', lat: '33.6844', lon: '73.0479' },
  { place_id: 1004, display_name: 'Rawalpindi, Punjab, Pakistan', lat: '33.5651', lon: '73.0169' },
  { place_id: 1005, display_name: 'Peshawar, Khyber Pakhtunkhwa, Pakistan', lat: '34.0151', lon: '71.5249' },
  { place_id: 1006, display_name: 'Quetta, Balochistan, Pakistan', lat: '30.1798', lon: '66.9750' },
  { place_id: 1007, display_name: 'Multan, Punjab, Pakistan', lat: '30.1575', lon: '71.5249' },
  { place_id: 1008, display_name: 'Faisalabad, Punjab, Pakistan', lat: '31.4504', lon: '73.1350' },
  { place_id: 1009, display_name: 'Hyderabad, Sindh, Pakistan', lat: '25.3960', lon: '68.3578' },
  { place_id: 1010, display_name: 'Sukkur, Sindh, Pakistan', lat: '27.7052', lon: '68.8574' },
  { place_id: 1011, display_name: 'Gwadar, Balochistan, Pakistan', lat: '25.1216', lon: '62.3254' },
  { place_id: 1012, display_name: 'Gilgit, Gilgit-Baltistan, Pakistan', lat: '35.9221', lon: '74.3087' },
  { place_id: 1013, display_name: 'Muzaffarabad, Azad Kashmir, Pakistan', lat: '34.3700', lon: '73.4711' },
  { place_id: 1014, display_name: 'Swat, Khyber Pakhtunkhwa, Pakistan', lat: '35.2227', lon: '72.4258' },
  { place_id: 1015, display_name: 'Dera Ismail Khan, Khyber Pakhtunkhwa, Pakistan', lat: '31.8626', lon: '70.9019' },
  { place_id: 1016, display_name: 'Larkana, Sindh, Pakistan', lat: '27.5590', lon: '68.2120' },
  { place_id: 1017, display_name: 'Sialkot, Punjab, Pakistan', lat: '32.4945', lon: '74.5229' },
  { place_id: 1018, display_name: 'Gujranwala, Punjab, Pakistan', lat: '32.1877', lon: '74.1945' },
  { place_id: 1019, display_name: 'Abbottabad, Khyber Pakhtunkhwa, Pakistan', lat: '34.1688', lon: '73.2215' },
  { place_id: 1020, display_name: 'Mirpur, Azad Kashmir, Pakistan', lat: '33.1484', lon: '73.7519' },
];

function getFallbackResults(query: string): SearchResult[] {
  const q = query.toLowerCase().trim();
  const matched = FALLBACK_LOCATIONS.filter((loc) =>
    loc.display_name.toLowerCase().includes(q)
  );
  return matched.length > 0 ? matched : FALLBACK_LOCATIONS.slice(0, 5);
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get('q');
  const lat = searchParams.get('lat');
  const lon = searchParams.get('lon');

  const headers = {
    'User-Agent': 'ReliefPulse-AI/1.0 (Disaster Relief Platform; contact: info@reliefpulse.org)',
    'Accept-Language': 'en,ur',
  };

  // 1. Reverse Geocoding
  if (lat && lon) {
    const cacheKey = `reverse:${parseFloat(lat).toFixed(4)},${parseFloat(lon).toFixed(4)}`;
    const cached = cache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
      return NextResponse.json(cached.data);
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);

      const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${encodeURIComponent(
        lat
      )}&lon=${encodeURIComponent(lon)}`;

      const res = await fetch(url, {
        headers,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        const result = {
          display_name: data.display_name || `${parseFloat(lat).toFixed(4)}, ${parseFloat(lon).toFixed(4)}`,
          lat,
          lon,
          address: data.address || {},
        };
        cache.set(cacheKey, { timestamp: Date.now(), data: result });
        return NextResponse.json(result);
      }
    } catch (err) {
      console.warn('Reverse geocode error, returning coordinate fallback:', err);
    }

    // Fallback response for coordinates
    const fallbackResult = {
      display_name: `Location (${parseFloat(lat).toFixed(4)}, ${parseFloat(lon).toFixed(4)})`,
      lat,
      lon,
    };
    return NextResponse.json(fallbackResult);
  }

  // 2. Search Query Geocoding
  if (q && q.trim()) {
    const trimmed = q.trim();
    const cacheKey = `search:${trimmed.toLowerCase()}`;
    const cached = cache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
      return NextResponse.json(cached.data);
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);

      // Search with priority for Pakistan
      const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
        trimmed
      )}&limit=8&countrycodes=pk`;

      const res = await fetch(url, {
        headers,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        let data: SearchResult[] = await res.json();
        // If no results specifically in Pakistan, try broader search
        if (!data || data.length === 0) {
          const broaderController = new AbortController();
          const broaderTimeout = setTimeout(() => broaderController.abort(), 3000);
          const broaderRes = await fetch(
            `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(trimmed)}&limit=5`,
            { headers, signal: broaderController.signal }
          );
          clearTimeout(broaderTimeout);
          if (broaderRes.ok) {
            data = await broaderRes.json();
          }
        }

        if (Array.isArray(data) && data.length > 0) {
          cache.set(cacheKey, { timestamp: Date.now(), data });
          return NextResponse.json(data);
        }
      }
    } catch (err) {
      console.warn('Geocoding search failed, providing fallback:', err);
    }

    // Fallback if upstream failed, timed out, or returned empty
    const fallbackResults = getFallbackResults(trimmed);
    return NextResponse.json(fallbackResults);
  }

  return NextResponse.json({ error: 'Missing query (q) or coordinates (lat, lon)' }, { status: 400 });
}
