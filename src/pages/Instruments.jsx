import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Plus, X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

// Sample rows shaped like the `instruments` table — replace with a
// supabase.from('instruments').select(...) query once schema is live.
const SAMPLE_INSTRUMENTS = [
  { instrument_id: "1", manufacturer: "Avery Berkel", model: "L223", instrument_type: "Platform Scale", accuracy_class: "III", Max: 300, Min: 2, e: 0.1, status: "active" },
  { instrument_id: "2", manufacturer: "Mettler Toledo", model: "IND560", instrument_type: "Bench Scale", accuracy_class: "II", Max: 15, Min: 0.02, e: 0.001, status: "active" },
  { instrument_id: "3", manufacturer: "Essae", model: "DS-415", instrument_type: "Weighbridge", accuracy_class: "III", Max: 60000, Min: 200, e: 20, status: "active" },
];

const NEW_INSTRUMENT_FIELDS = [
  ["manufacturer", "Manufacturer"],
  ["model", "Model"],
  ["type_designation", "Type designation"],
  ["serial_number", "Serial number"],
  ["instrument_type", "Instrument type"],
  ["instrument_category", "Instrument category"],
  ["Max", "Max"],
  ["Min", "Min"],
  ["e", "e (scale interval)"],
  ["d", "d (verification interval)"],
  ["n", "n (number of intervals)"],
  ["unit", "Unit"],
];

export default function Instruments() {
  const [query, setQuery] = useState("");
  const [showForm, setShowForm] = useState(false);

  const filtered = SAMPLE_INSTRUMENTS.filter((i) =>
    `${i.manufacturer} ${i.model} ${i.instrument_type}`.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Instruments</h1>
          <p className="text-sm text-muted-foreground">Master data for every instrument submitted to your lab.</p>
        </div>
        <Button onClick={() => setShowForm(true)}>
          <Plus className="h-4 w-4" /> Register instrument
        </Button>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search manufacturer, model, type…"
          className="w-full rounded-lg border border-input bg-surface py-2 pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      <Card>
        <CardContent className="pt-5">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-muted-foreground">
                <th className="pb-2 font-medium">Manufacturer</th>
                <th className="pb-2 font-medium">Model</th>
                <th className="pb-2 font-medium">Type</th>
                <th className="pb-2 font-medium">Accuracy class</th>
                <th className="pb-2 font-medium">Max / Min / e</th>
                <th className="pb-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((inst, i) => (
                <motion.tr
                  key={inst.instrument_id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="cursor-pointer border-t border-border hover:bg-muted/50"
                  data-cursor-hover
                >
                  <td className="py-2.5 font-medium">{inst.manufacturer}</td>
                  <td className="py-2.5">{inst.model}</td>
                  <td className="py-2.5 text-muted-foreground">{inst.instrument_type}</td>
                  <td className="py-2.5 font-num">{inst.accuracy_class}</td>
                  <td className="py-2.5 font-num text-xs text-muted-foreground">
                    {inst.Max} / {inst.Min} / {inst.e}
                  </td>
                  <td className="py-2.5">
                    <span className="rounded-full bg-status-pass/10 px-2 py-0.5 text-xs font-medium text-status-pass">
                      {inst.status}
                    </span>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <AnimatePresence>
        {showForm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
            onClick={() => setShowForm(false)}
          >
            <motion.div
              initial={{ opacity: 0, y: 16, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.98 }}
              transition={{ type: "spring", stiffness: 320, damping: 28 }}
              onClick={(e) => e.stopPropagation()}
              className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-border bg-surface p-6 shadow-raised"
            >
              <div className="mb-4 flex items-center justify-between">
                <h2 className="font-heading text-lg font-semibold">Register instrument</h2>
                <button onClick={() => setShowForm(false)} data-cursor-hover>
                  <X className="h-5 w-5 text-muted-foreground" />
                </button>
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  setShowForm(false);
                }}
                className="grid gap-3 sm:grid-cols-2"
              >
                {NEW_INSTRUMENT_FIELDS.map(([key, label]) => (
                  <div key={key}>
                    <label className="text-sm font-medium">{label}</label>
                    <input
                      name={key}
                      className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                ))}
                <div className="mt-2 sm:col-span-2">
                  <Button type="submit" className="w-full">Save instrument</Button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
