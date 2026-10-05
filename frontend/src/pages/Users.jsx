import React, { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useForm } from "react-hook-form";
import { Plus, X, Pencil, ChevronDown, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { SessionStatus } from "@/components/ui/SessionStatus";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/apiClient";
import { CAPABILITY_TEXT, roleLabel, roleTone, sortCapabilities } from "@/lib/roles";
import { cn } from "@/lib/utils";

const inputCls =
  "mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring";

function Modal({ title, onClose, children }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, y: 16, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 10, scale: 0.98 }}
        transition={{ type: "spring", stiffness: 320, damping: 28 }}
        onClick={(e) => e.stopPropagation()}
        className="max-h-[92vh] w-full max-w-md overflow-y-auto rounded-2xl border border-border bg-surface p-6 shadow-raised"
        role="dialog"
        aria-label={title}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-heading text-lg font-semibold">{title}</h2>
          <button onClick={onClose} aria-label="Close" data-cursor-hover>
            <X className="h-5 w-5 text-muted-foreground" />
          </button>
        </div>
        {children}
      </motion.div>
    </motion.div>
  );
}

function RolePicker({ roles, register, name = "role", selected }) {
  const groups = useMemo(() => {
    const out = {};
    roles.filter((r) => r.assignable).forEach((r) => {
      (out[r.group] = out[r.group] || []).push(r);
    });
    return out;
  }, [roles]);
  const info = roles.find((r) => r.code === selected);

  return (
    <div>
      <label className="text-sm font-medium" htmlFor={name}>Role</label>
      <select id={name} {...register(name, { required: true })} className={inputCls}>
        {Object.entries(groups).map(([group, list]) => (
          <optgroup key={group} label={group}>
            {list.map((r) => <option key={r.code} value={r.code}>{r.label}</option>)}
          </optgroup>
        ))}
      </select>
      {info && <p className="mt-1.5 text-xs leading-snug text-muted-foreground">{info.summary}</p>}
    </div>
  );
}

function RoleGuide({ roles }) {
  const [open, setOpen] = useState(false);
  const ordered = [...roles].sort((a, b) => (a.level || 9) - (b.level || 9));

  return (
    <Card>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between px-5 py-4 text-left"
        data-cursor-hover
      >
        <span className="flex items-center gap-2 font-heading text-base font-semibold">
          <ShieldCheck className="h-4 w-4 text-primary" /> Roles &amp; responsibilities
        </span>
        <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition", open && "rotate-180")} />
      </button>
      {open && (
        <CardContent className="space-y-4 pt-0">
          <p className="text-sm text-muted-foreground">
            Roles follow ISO/IEC 17025. The most important rule: <span className="font-medium text-foreground">whoever tested a session can never review or sign it.</span>
          </p>
          <div className="grid gap-3 md:grid-cols-2">
            {ordered.map((r) => (
              <div key={r.code} className="rounded-lg border border-border p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-medium", roleTone(r.code))}>{r.label}</span>
                  <span className="text-[11px] text-muted-foreground">{r.group}</span>
                </div>
                <p className="mt-2 text-xs leading-snug text-muted-foreground">{r.summary}</p>
                <ul className="mt-2 space-y-0.5 text-xs">
                  {sortCapabilities(r.capabilities).map((c) => <li key={c}>· {CAPABILITY_TEXT[c] || c}</li>)}
                  {r.capabilities.length === 0 && <li className="text-muted-foreground">· Read-only</li>}
                </ul>
              </div>
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
}

export default function Users() {
  const { token, can, profile } = useAuth();
  const canManage = can("users.manage");
  const canAuthorise = can("users.authorize");

  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [tests, setTests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [submitError, setSubmitError] = useState("");

  const add = useForm({ defaultValues: { role: "TESTER" } });
  const edit = useForm();

  async function load() {
    setLoading(true);
    setLoadError("");
    try {
      const [u, r, td] = await Promise.all([
        api.getUsers(token),
        api.getRoles(token),
        api.getTestDefinitions(token).catch(() => []),
      ]);
      setUsers(u);
      setRoles(r);
      const seen = new Map();
      td.forEach((t) => !seen.has(t.test_code) && seen.set(t.test_code, t));
      setTests([...seen.values()]);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) load();
  }, [token]);

  async function onAdd(values) {
    setSubmitError("");
    try {
      await api.createUser(values, token);
      add.reset({ role: "TESTER" });
      setShowForm(false);
      load();
    } catch (err) {
      setSubmitError(err.message);
    }
  }

  function openEdit(u) {
    setSubmitError("");
    setEditing(u);
    edit.reset({
      role: u.role,
      status: u.status || "ACTIVE",
      designation: u.designation || "",
      test_codes: u.authorization_scope?.test_codes || [],
    });
  }

  async function onEdit(values) {
    setSubmitError("");
    // A lone ticked checkbox arrives as a string, none as false: always a list.
    const raw = values.test_codes;
    const codes = Array.isArray(raw) ? raw : raw ? [raw] : [];
    const scope = { ...(editing.authorization_scope || {}), test_codes: codes };
    if (!codes.length) delete scope.test_codes;

    const payload = canManage
      ? {
          role: editing.role === "LAB_ADMIN" ? undefined : values.role,
          status: values.status,
          designation: values.designation,
          authorization_scope: scope,
        }
      : { authorization_scope: scope };

    try {
      await api.updateUser(editing.user_id, payload, token);
      setEditing(null);
      load();
    } catch (err) {
      setSubmitError(err.message);
    }
  }

  const isMe = (u) => u.user_id === profile?.user_id;
  const roleChoice = add.watch("role");
  const editRole = edit.watch("role");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Staff &amp; Roles</h1>
          <p className="text-sm text-muted-foreground">
            {canManage
              ? "The people in your laboratory and what each is responsible for."
              : "The people in your laboratory and their roles."}
          </p>
        </div>
        {canManage && (
          <Button onClick={() => { setSubmitError(""); setShowForm(true); }}>
            <Plus className="h-4 w-4" /> Add staff member
          </Button>
        )}
      </div>

      {roles.length > 0 && <RoleGuide roles={roles} />}

      <Card>
        <CardContent className="pt-5">
          {loading && <p className="py-6 text-center text-sm text-muted-foreground">Loading staff…</p>}
          {loadError && <p className="py-6 text-center text-sm text-status-fail">{loadError}</p>}
          {!loading && !loadError && users.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-muted-foreground">
                    <th className="pb-2 font-medium">Name</th>
                    <th className="pb-2 font-medium">Role</th>
                    <th className="pb-2 font-medium">Designation</th>
                    <th className="pb-2 font-medium">Authorised tests</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2" />
                  </tr>
                </thead>
                <tbody>
                  {users.map((u, i) => {
                    const codes = u.authorization_scope?.test_codes;
                    const testing = ["TESTER", "ASSISTANT"].includes(u.role);
                    return (
                      <motion.tr
                        key={u.user_id}
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.04 }}
                        className="border-t border-border"
                      >
                        <td className="py-2.5">
                          <span className="font-medium">{u.first_name} {u.last_name || ""}</span>
                          {isMe(u) && <span className="ml-1.5 text-xs text-muted-foreground">(you)</span>}
                          <span className="block text-xs text-muted-foreground">{u.email}</span>
                        </td>
                        <td className="py-2.5">
                          <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-medium", roleTone(u.role))}>
                            {u.role_label || roleLabel(u.role)}
                          </span>
                        </td>
                        <td className="py-2.5 text-muted-foreground">{u.designation || "—"}</td>
                        <td className="py-2.5 text-xs text-muted-foreground">
                          {!testing ? "—" : codes?.length ? (
                            <span className="font-num">{codes.join(", ")}</span>
                          ) : "All tests"}
                        </td>
                        <td className="py-2.5"><SessionStatus status={(u.status || "ACTIVE").toUpperCase()} /></td>
                        <td className="py-2.5 text-right">
                          {(canManage || canAuthorise) && !(isMe(u) && !canAuthorise) && (
                            <button
                              type="button"
                              onClick={() => openEdit(u)}
                              className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                              aria-label={`Edit ${u.first_name}`}
                              data-cursor-hover
                            >
                              <Pencil className="h-4 w-4" />
                            </button>
                          )}
                        </td>
                      </motion.tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <AnimatePresence>
        {showForm && (
          <Modal title="Add staff member" onClose={() => setShowForm(false)}>
            <form onSubmit={add.handleSubmit(onAdd)} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-medium">First name</label>
                  <input {...add.register("first_name", { required: true })} className={inputCls} />
                </div>
                <div>
                  <label className="text-sm font-medium">Last name</label>
                  <input {...add.register("last_name")} className={inputCls} />
                </div>
              </div>
              <div>
                <label className="text-sm font-medium">Email</label>
                <input type="email" {...add.register("email", { required: true })} className={inputCls} />
              </div>
              <div>
                <label className="text-sm font-medium">Temporary password</label>
                <input type="password" {...add.register("password", { required: true })} className={inputCls} />
              </div>
              <RolePicker roles={roles} register={add.register} selected={roleChoice} />
              <div>
                <label className="text-sm font-medium">Designation (optional)</label>
                <input
                  placeholder="e.g. Assistant Director"
                  {...add.register("designation")}
                  className={inputCls}
                />
                <p className="mt-1 text-xs text-muted-foreground">Government labs use their own titles; the role decides what the person can do.</p>
              </div>
              {submitError && <p className="text-xs text-status-fail">{submitError}</p>}
              <Button type="submit" className="w-full" disabled={add.formState.isSubmitting}>
                {add.formState.isSubmitting ? "Adding…" : "Add staff member"}
              </Button>
            </form>
          </Modal>
        )}

        {editing && (
          <Modal title={`Edit ${editing.first_name}`} onClose={() => setEditing(null)}>
            <form onSubmit={edit.handleSubmit(onEdit)} className="space-y-3">
              {canManage && editing.role !== "LAB_ADMIN" && !isMe(editing) && (
                <RolePicker roles={roles} register={edit.register} selected={editRole} />
              )}
              {canManage && (
                <>
                  <div>
                    <label className="text-sm font-medium">Designation</label>
                    <input {...edit.register("designation")} className={inputCls} />
                  </div>
                  {!isMe(editing) && editing.role !== "LAB_ADMIN" && (
                    <div>
                      <label className="text-sm font-medium">Account</label>
                      <select {...edit.register("status")} className={inputCls}>
                        <option value="ACTIVE">Active</option>
                        <option value="INACTIVE">Deactivated (cannot sign in)</option>
                        <option value="SUSPENDED">Suspended</option>
                      </select>
                    </div>
                  )}
                </>
              )}
              {canAuthorise && ["TESTER", "ASSISTANT"].includes(editing.role) && tests.length > 0 && (
                <fieldset>
                  <legend className="text-sm font-medium">Authorised for these tests</legend>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Tick the tests this person is competent to run. Leave all unticked to authorise every test.
                  </p>
                  <div className="mt-2 grid gap-1.5">
                    {tests.map((t) => (
                      <label key={t.test_code} className="flex items-center gap-2 text-sm">
                        <input type="checkbox" value={t.test_code} {...edit.register("test_codes")} />
                        <span className="font-num text-xs">{t.test_code}</span>
                        <span className="text-muted-foreground">{t.test_name}</span>
                      </label>
                    ))}
                  </div>
                </fieldset>
              )}
              {submitError && <p className="text-xs text-status-fail">{submitError}</p>}
              <Button type="submit" className="w-full" disabled={edit.formState.isSubmitting}>
                {edit.formState.isSubmitting ? "Saving…" : "Save changes"}
              </Button>
            </form>
          </Modal>
        )}
      </AnimatePresence>
    </div>
  );
}
