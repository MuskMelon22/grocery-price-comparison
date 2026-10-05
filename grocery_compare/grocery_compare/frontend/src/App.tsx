import { Link, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import { EmptyState, Toaster } from "./components/ui";
import About from "./pages/About";
import Analytics from "./pages/Analytics";
import Basket from "./pages/Basket";
import Home from "./pages/Home";
import ProductDetail from "./pages/ProductDetail";
import SearchResults from "./pages/SearchResults";

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/search" element={<SearchResults />} />
          <Route path="/product/:id" element={<ProductDetail />} />
          <Route path="/basket" element={<Basket />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/about" element={<About />} />
          <Route path="*" element={<div className="py-10"><EmptyState title="Page not found"><Link to="/" className="underline">Go home</Link></EmptyState></div>} />
        </Routes>
      </main>
      <footer className="border-t border-slate-200 py-6 text-center text-xs text-slate-500 dark:border-slate-800">
        Educational project · prices scraped from BigBasket &amp; JioMart may be outdated · <Link to="/about" className="underline">About &amp; disclaimer</Link>
      </footer>
      <Toaster />
    </div>
  );
}
