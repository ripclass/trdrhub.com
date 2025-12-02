/**
 * Vercel Edge Function - Geo Detection
 * 
 * Returns the user's country based on Vercel's IP geolocation headers.
 * This is FREE and included with Vercel deployments.
 */

import type { VercelRequest, VercelResponse } from '@vercel/node';

export default function handler(req: VercelRequest, res: VercelResponse) {
  // Vercel automatically provides these headers
  const country = req.headers['x-vercel-ip-country'] as string || 'US';
  const city = req.headers['x-vercel-ip-city'] as string || '';
  const region = req.headers['x-vercel-ip-country-region'] as string || '';

  // Set CORS headers for frontend access
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET');
  res.setHeader('Cache-Control', 'no-store'); // Don't cache - IP can change

  return res.status(200).json({
    country,
    city,
    region,
    detected: true,
  });
}

