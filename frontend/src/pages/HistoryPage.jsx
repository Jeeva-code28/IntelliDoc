import React from 'react';
import { Link } from 'react-router-dom';

export default function HistoryPage() {
  return (
    <div className="flex h-screen w-screen items-center justify-center bg-[var(--color-bg-main)] text-white">
      <div className="flex flex-col gap-4 items-center">
        <h1 className="text-2xl font-bold">History & Archives Placeholder</h1>
        <Link to="/" className="text-[var(--color-primary-cyan)] hover:underline">
          Back to Chat
        </Link>
      </div>
    </div>
  );
}
