import { useState } from "react";
import { Link, NavLink, useLocation, useSearchParams } from "react-router-dom";
import { basketStore, pincodeStore, themeStore, toggleTheme } from "../store";
import PincodeModal from "./PincodeModal";
import SearchBar from "./SearchBar";

const link = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-1.5 text-sm ${isActive ? "bg-emerald-50 font-semibold text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" : "hover:bg-slate-100 dark:hover:bg-slate-800"}`;

export default function Navbar() {
  const count = basketStore.use().reduce((n, i) => n + i.qty, 0);
  const pincode = pincodeStore.use();
  const theme = themeStore.use();
  const [pinOpen, setPinOpen] = useState(false);
  const { pathname } = useLocation();
  const [params] = useSearchParams();

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/85 backdrop-blur dark:border-slate-800 dark:bg-slate-950/85">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-3">
        <Link to="/" className="text-lg font-bold">🛒 Grocery<span className="text-emerald-600">Compare</span></Link>
        {pathname !== "/" && (
          <div className="order-last w-full sm:order-none sm:w-auto sm:flex-1 sm:max-w-md">
            <SearchBar key={params.get("q")} initial={params.get("q") ?? ""} />
          </div>
        )}
        <nav className="ml-auto flex items-center gap-1">
          <button onClick={() => setPinOpen(true)} className="rounded-full border border-slate-300 px-3 py-1 text-sm dark:border-slate-700" title="Change delivery pincode">
            📍 {pincode}
          </button>
          <NavLink to="/analytics" className={link}>Analytics</NavLink>
          <NavLink to="/basket" className={link}>
            Basket{count > 0 && <span className="ml-1 rounded-full bg-emerald-600 px-1.5 text-xs text-white">{count}</span>}
          </NavLink>
          <button onClick={toggleTheme} aria-label="Toggle dark mode" className="rounded-lg px-2 py-1.5 hover:bg-slate-100 dark:hover:bg-slate-800">
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
        </nav>
      </div>
      {pinOpen && <PincodeModal onClose={() => setPinOpen(false)} />}
    </header>
  );
}
