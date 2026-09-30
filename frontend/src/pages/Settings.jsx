import React, { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/apiClient";

export default function Settings() {
  const { token, role } = useAuth();
  const [profile, setProfile] = useState(null);
  const [lab, setLab] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [profileMsg, setProfileMsg] = useState("");
  const [labMsg, setLabMsg] = useState("");
  const [labLoadError, setLabLoadError] = useState("");

  const profileForm = useForm();
  const labForm = useForm();

  useEffect(() => {
    if (!token) return;
    (async () => {
      setLoading(true);
      setLoadError("");
      setLabLoadError("");
      try {
        const [p, l] = await Promise.all([
          api.getMyProfile(token),
          // A lab failure must not block the profile section, but it must not be silent either.
          api.getMyLaboratory(token).catch((err) => {
            setLabLoadError(err.message || "Could not load laboratory details.");
            return null;
          }),
        ]);
        setProfile(p);
        setLab(l);
        profileForm.reset(p);
        if (l) labForm.reset(l);
      } catch (err) {
        setLoadError(err.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  async function onSaveProfile(values) {
    setProfileMsg("");
    try {
      const payload = Object.fromEntries(
        Object.entries(values).filter(([k]) => ["employee_id", "first_name", "last_name", "phone", "designation", "qualification"].includes(k))
      );
      await api.updateMyProfile(payload, token);
      setProfileMsg("Saved.");
    } catch (err) {
      setProfileMsg(err.message);
    }
  }

  async function onSaveLab(values) {
    setLabMsg("");
    try {
      const payload = Object.fromEntries(
        Object.entries(values).filter(([k]) => k !== "laboratory_id" && k !== "laboratory_code" && k !== "created_at" && k !== "updated_at")
      );
      await api.updateMyLaboratory(payload, token);
      setLabMsg("Saved.");
    } catch (err) {
      setLabMsg(err.message);
    }
  }

  if (loading) return <p className="py-12 text-center text-sm text-muted-foreground">Loading…</p>;
  if (loadError) return <p className="py-12 text-center text-sm text-status-fail">{loadError}</p>;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-muted-foreground">Your profile and laboratory details.</p>
      </div>

      <Card>
        <CardHeader><CardTitle>Your profile</CardTitle></CardHeader>
        <CardContent className="pt-0">
          <form onSubmit={profileForm.handleSubmit(onSaveProfile)} className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="text-sm font-medium">First name</label>
              <input {...profileForm.register("first_name")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-sm font-medium">Last name</label>
              <input {...profileForm.register("last_name")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-sm font-medium">Phone</label>
              <input {...profileForm.register("phone")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-sm font-medium">Designation</label>
              <input {...profileForm.register("designation")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" />
            </div>
            <div className="sm:col-span-2">
              <p className="text-xs text-muted-foreground">Email: {profile?.email} · Role: <span className="capitalize">{role?.toLowerCase()}</span></p>
            </div>
            <div className="sm:col-span-2 flex items-center gap-3">
              <Button type="submit" size="sm" disabled={profileForm.formState.isSubmitting}>
                {profileForm.formState.isSubmitting ? "Saving…" : "Save profile"}
              </Button>
              {profileMsg && <span className="text-xs text-muted-foreground">{profileMsg}</span>}
            </div>
          </form>
        </CardContent>
      </Card>

      {labLoadError && (
        <p className="text-sm text-status-fail">Couldn't load laboratory details: {labLoadError}</p>
      )}

      {lab && (
        <Card>
          <CardHeader><CardTitle>Laboratory</CardTitle></CardHeader>
          <CardContent className="pt-0">
            <form onSubmit={labForm.handleSubmit(onSaveLab)} className="grid gap-3 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="text-sm font-medium">Name</label>
                <input {...labForm.register("name")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-sm font-medium">City</label>
                <input {...labForm.register("city")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-sm font-medium">Phone</label>
                <input {...labForm.register("phone")} className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" />
              </div>
              <div className="sm:col-span-2 flex items-center gap-3">
                <Button type="submit" size="sm" disabled={labForm.formState.isSubmitting}>
                  {labForm.formState.isSubmitting ? "Saving…" : "Save laboratory"}
                </Button>
                {labMsg && <span className="text-xs text-muted-foreground">{labMsg}</span>}
              </div>
            </form>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
