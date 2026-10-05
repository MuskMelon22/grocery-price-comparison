import { useEffect, useRef, useState, type FormEvent } from "react";
import { pincodeStore } from "../store";

/** Prices depend on delivery location, so the pincode is part of every search. */
export default function PincodeModal({ onClose, onSave }: { onClose: () => void; onSave?: (pin: string) => void }) {
  const [pin, setPin] = useState(pincodeStore.get());
  const ref = useRef<HTMLDialogElement>(null);
  const valid = /^\d{6}$/.test(pin);

  useEffect(() => {
    ref.current?.showModal();
  }, []);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!valid) return;
    pincodeStore.set(pin);
    onSave?.(pin);
    onClose();
  }

  return (
    <dialog ref={ref} onClose={onClose} onClick={(e) => e.target === ref.current && onClose()}
      className="m-auto w-[min(92vw,380px)] rounded-2xl bg-white p-0 text-slate-900 backdrop:bg-black/50 dark:bg-slate-900 dark:text-slate-100">
      <form onSubmit={submit} className="space-y-4 p-6">
        <h2 className="text-lg font-semibold">Delivery pincode</h2>
        <p className="text-sm text-slate-500">Prices and stock differ by location.</p>
        <input autoFocus inputMode="numeric" maxLength={6} value={pin} aria-label="Pincode"
          onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
          className="w-full rounded-xl border border-slate-300 bg-transparent px-4 py-3 text-lg tracking-widest outline-none focus:border-emerald-500 dark:border-slate-700" />
        {!valid && pin.length > 0 && <p className="text-sm text-red-600">Enter a 6-digit pincode.</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-xl px-4 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">Cancel</button>
          <button disabled={!valid} className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">Save</button>
        </div>
      </form>
    </dialog>
  );
}
