import React from 'react';

export default function CoordinatorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div
      suppressHydrationWarning
      className="min-h-screen bg-[#060913] text-warm-white flex flex-col font-sans"
    >
      {children}
    </div>
  );
}
