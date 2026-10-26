import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, ArrowLeft, Archive, Calendar, MessageSquare, Trash2 } from 'lucide-react';

export default function HistoryPage() {
  const navigate = useNavigate();
  const [archives, setArchives] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/history')
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setArchives(data))
      .catch((err) => console.error('Error fetching archives:', err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen w-full bg-[#090909] text-[#F5F1EC] font-sans flex flex-col">
      <header className="h-16 border-b border-[#2B2B2B] bg-[#101010] px-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#F15A24] flex items-center justify-center text-white font-bold text-xs">
            ID
          </div>
          <span className="font-bold text-sm tracking-tight text-[#F5F1EC]">
            IntelliDoc Archives
          </span>
        </div>

        <button
          onClick={() => navigate('/workspace')}
          className="flex items-center gap-2 text-xs text-[#A3A3A3] hover:text-[#F5F1EC] transition-colors cursor-pointer"
        >
          <ArrowLeft size={14} />
          <span>Back to Workspace</span>
        </button>
      </header>

      <main className="max-w-4xl mx-auto w-full px-6 py-10 flex-1">
        <div className="mb-8">
          <h1 className="text-2xl font-bold font-heading text-[#F5F1EC] mb-1">
            Archived Conversations
          </h1>
          <p className="text-xs text-[#A3A3A3]">
            Audit logs and exported records of past sessions and citations.
          </p>
        </div>

        {loading ? (
          <div className="text-xs text-[#A3A3A3]">Loading archives...</div>
        ) : archives.length === 0 ? (
          <div className="p-8 border border-dashed border-[#2B2B2B] rounded-2xl bg-[#171717] text-center text-xs text-[#737373]">
            No archived conversations found.
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {archives.map((a) => (
              <div
                key={a.id}
                className="p-4 bg-[#171717] border border-[#2B2B2B] rounded-xl flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <Archive size={18} className="text-[#F15A24]" />
                  <div>
                    <h3 className="text-sm font-semibold text-[#F5F1EC] m-0">{a.title}</h3>
                    <div className="flex items-center gap-2 text-[11px] text-[#A3A3A3] mt-0.5">
                      <span className="flex items-center gap-1">
                        <Calendar size={11} />
                        {new Date(a.deleted_at || a.created_at).toLocaleDateString()}
                      </span>
                      <span>•</span>
                      <span>{a.message_count} messages</span>
                      <span>•</span>
                      <span>{a.document_count} documents</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
