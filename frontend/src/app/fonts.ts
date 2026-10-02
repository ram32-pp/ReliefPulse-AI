import localFont from 'next/font/local';

export const geistSans = localFont({
  src: './fonts/Geist-Variable.woff2',
  variable: '--font-geist-sans',
  display: 'swap',
  weight: '100 900',
});

export const geistMono = localFont({
  src: './fonts/GeistMono-Variable.woff2',
  variable: '--font-geist-mono',
  display: 'swap',
  weight: '100 900',
});
