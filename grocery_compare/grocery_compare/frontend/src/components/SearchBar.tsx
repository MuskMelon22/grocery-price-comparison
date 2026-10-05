import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { pincodeStore, toast } from "../store";

export default function SearchBar({ initial = "", large = false }: { initial?: string; large?: boolean }) {
  const [q, setQ] = useState(initial);
  const navigate = useNavigate();

  function submit(e: FormEvent) {
    e.preventDefault();
    const query = q.trim();
    if (query.length < 2 || query.length > 60) return toast("Search must be 2-60 characters", "error");
    navigate(`/search?${new URLSearchParams({ q: query, pincode: pincodeStore.get() })}`);
  }

  const size = large ? "py-4 pl-5 pr-28 text-lg" : "py-2 pl-4 pr-20 text-sm";
  return (
    <form onSubmit={submit} role="search" className="relative w-full">
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search milk, atta, amul butter 500g..."
        aria-label="Search groceries" maxLength={60}
        className={`w-full rounded-full border border-slate-300 bg-white shadow-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-700 dark:bg-slate-900 ${size}`} />
      <button className={`absolute top-1/2 right-1.5 -translate-y-1/2 rounded-full bg-emerald-600 font-semibold text-white hover:bg-emerald-700 ${large ? "px-6 py-2.5" : "px-4 py-1 text-sm"}`}>
        Search
      </button>
    </form>
  );
}
