import { useState } from "react";
import { Link } from "react-router-dom";
import PincodeModal from "../components/PincodeModal";
import SearchBar from "../components/SearchBar";
import { pincodeStore } from "../store";

const POPULAR = ["milk", "atta", "eggs", "butter", "rice", "sugar", "tea", "sunflower oil", "toor dal", "paneer", "bread", "maggi"];
const STEPS = [
  ["🔎", "Search once", "We check BigBasket and JioMart for your pincode."],
  ["⚖️", "Compare fairly", "Matched products side by side, with price per 100 g / 100 ml."],
  ["🧺", "Save on the basket", "Build a basket and see the cheapest store split."],
];

export default function Home() {
  const pincode = pincodeStore.use();
  const [pinOpen, setPinOpen] = useState(false);
  return (
    <div className="space-y-16 py-10 sm:py-20">
      <section className="mx-auto max-w-2xl space-y-6 text-center">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
          Which store is <span className="text-emerald-600">cheaper</span> today?
        </h1>
        <p className="text-slate-500">Live prices from <b className="text-lime-600">BigBasket</b> and <b className="text-sky-600">JioMart</b>, side by side.</p>
        <SearchBar large />
        <button onClick={() => setPinOpen(true)} className="rounded-full border border-slate-300 px-4 py-1.5 text-sm dark:border-slate-700">
          📍 Delivering to <b>{pincode}</b> · change
        </button>
        <div className="flex flex-wrap justify-center gap-2">
          {POPULAR.map((q) => (
            <Link key={q} to={`/search?${new URLSearchParams({ q, pincode })}`}
              className="rounded-full bg-white px-3 py-1 text-sm shadow-sm ring-1 ring-slate-200 hover:ring-emerald-500 dark:bg-slate-900 dark:ring-slate-800">
              {q}
            </Link>
          ))}
        </div>
      </section>
      <section className="grid gap-4 sm:grid-cols-3">
        {STEPS.map(([icon, title, text]) => (
          <div key={title} className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200 dark:bg-slate-900 dark:ring-slate-800">
            <div className="text-3xl">{icon}</div>
            <h3 className="mt-2 font-semibold">{title}</h3>
            <p className="text-sm text-slate-500">{text}</p>
          </div>
        ))}
      </section>
      {pinOpen && <PincodeModal onClose={() => setPinOpen(false)} />}
    </div>
  );
}
