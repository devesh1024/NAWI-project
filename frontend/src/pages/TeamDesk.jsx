import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Scale, Search, X } from "lucide-react";
import { api } from "@/lib/apiClient";
import { useAuth } from "@/hooks/useAuth";
import { useChat } from "@/hooks/useChat";
import { cn } from "@/lib/utils";
import { Avatar } from "@/components/chat/Avatar";
import { ChatPane } from "@/components/chat/ChatPane";
import { listTime, preview, roleLabel } from "@/components/chat/chatUtils";

const STATUS_COPY = {
  online: { dot: "bg-status-pass", text: "Live" },
  connecting: { dot: "bg-status-pending", text: "Connecting…" },
  offline: { dot: "bg-status-na", text: "Reconnecting…" },
};

export default function TeamDesk() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();
  const chat = useChat();
  const { conversations, loaded, status, online, typing, me, setActiveConversation, refreshConversations } = chat;

  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null); // null = not searching
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [startError, setStartError] = useState("");
  const drafts = useRef({});
  const refetched = useRef(new Set());

  const selected = conversations.find((c) => c.conversation_id === conversationId) || null;

  // The chat being viewed decides whether incoming messages show a card.
  useEffect(() => {
    setActiveConversation(selected ? selected.conversation_id : null);
    return () => setActiveConversation(null);
  }, [selected?.conversation_id, setActiveConversation]); // eslint-disable-line react-hooks/exhaustive-deps

  // A deep link to a conversation we haven't listed yet: look once more, then give up.
  useEffect(() => {
    if (conversationId && loaded && !selected && !refetched.current.has(conversationId)) {
      refetched.current.add(conversationId);
      refreshConversations();
    }
  }, [conversationId, loaded, selected, refreshConversations]);

  const notFound = !!conversationId && loaded && !selected && refetched.current.has(conversationId);

  // Debounced people search.
  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setResults(null);
      setSearching(false);
      setSearchError("");
      return undefined;
    }
    let cancelled = false;
    setSearching(true);
    const timer = setTimeout(async () => {
      try {
        const found = await api.searchChatUsers(q, token);
        if (!cancelled) {
          setResults(found);
          setSearchError("");
        }
      } catch (err) {
        if (!cancelled) setSearchError(err.message);
      } finally {
        if (!cancelled) setSearching(false);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, token]);

  async function startChat(user) {
    setStartError("");
    try {
      const cid = await chat.openConversationWith(user.user_id);
      setQuery("");
      navigate(`/app/teamdesk/${cid}`);
    } catch (err) {
      setStartError(err.message);
    }
  }

  const conn = STATUS_COPY[status] || STATUS_COPY.connecting;
  const existingWith = new Map(conversations.map((c) => [c.other_user.user_id, c]));

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* ------------------------------------------------ left: people + chats (30%) */}
      <aside
        className={cn(
          "flex w-full flex-col border-r border-border bg-surface md:w-[30%] md:min-w-[300px]",
          conversationId && "hidden md:flex"
        )}
      >
        <div className="space-y-3 border-b border-border px-4 pb-3 pt-4">
          <div className="flex items-center justify-between">
            <h1 className="font-heading text-xl font-semibold">TeamDesk</h1>
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground" role="status">
              <span className={cn("h-2 w-2 rounded-full", conn.dot)} aria-hidden="true" />
              {conn.text}
            </span>
          </div>

          <button
            type="button"
            onClick={() => navigate("/app/dashboard")}
            className="flex w-full items-center gap-2 rounded-xl border border-border px-3 py-2 text-sm font-medium hover:bg-muted"
            data-cursor-hover
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </button>

          <label className="relative block">
            <span className="sr-only">Search people to start a conversation</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search people by name or email"
              className="h-10 w-full rounded-xl border border-input bg-background pl-9 pr-9 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-muted-foreground hover:bg-muted"
                aria-label="Clear search"
                data-cursor-hover
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </label>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          {startError && <p className="px-4 py-2 text-xs text-status-fail">{startError}</p>}

          {results !== null || searching || searchError ? (
            <PeopleResults
              results={results}
              searching={searching}
              error={searchError}
              existingWith={existingWith}
              onPick={startChat}
            />
          ) : (
            <ConversationList
              conversations={conversations}
              loaded={loaded}
              selectedId={conversationId}
              online={online}
              typing={typing}
              meId={me?.user_id}
              onPick={(cid) => navigate(`/app/teamdesk/${cid}`)}
            />
          )}
        </div>
      </aside>

      {/* -------------------------------------------------------- right: chat (70%) */}
      <main className={cn("min-w-0 flex-1", !conversationId && "hidden md:flex")}>
        {selected ? (
          <ChatPane
            key={selected.conversation_id}
            conversation={selected}
            drafts={drafts}
            onBack={() => navigate("/app/teamdesk")}
          />
        ) : (
          <EmptyState notFound={notFound} onBack={() => navigate("/app/teamdesk")} />
        )}
      </main>
    </div>
  );
}

function ConversationList({ conversations, loaded, selectedId, online, typing, meId, onPick }) {
  if (!loaded) return <p className="px-4 py-8 text-center text-sm text-muted-foreground">Loading conversations…</p>;

  if (conversations.length === 0) {
    return (
      <div className="px-6 py-12 text-center">
        <p className="font-heading text-sm font-semibold">No conversations yet</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Search for a colleague above to start your first one.
        </p>
      </div>
    );
  }

  return (
    <ul>
      {conversations.map((c) => {
        const last = c.last_message;
        const isTyping = !!typing[c.conversation_id];
        const active = c.conversation_id === selectedId;
        return (
          <li key={c.conversation_id}>
            <button
              type="button"
              onClick={() => onPick(c.conversation_id)}
              aria-current={active ? "true" : undefined}
              className={cn(
                "flex w-full items-center gap-3 border-b border-border/60 px-4 py-3 text-left hover:bg-muted",
                active && "bg-muted"
              )}
              data-cursor-hover
            >
              <Avatar user={c.other_user} online={!!online[c.other_user.user_id]} />
              <span className="min-w-0 flex-1">
                <span className="flex items-baseline justify-between gap-2">
                  <span className="truncate text-sm font-medium">{c.other_user.name}</span>
                  <span
                    className={cn(
                      "font-num shrink-0 text-[11px]",
                      c.unread_count ? "font-semibold text-primary" : "text-muted-foreground"
                    )}
                  >
                    {last ? listTime(c.last_message_at) : ""}
                  </span>
                </span>
                <span className="mt-0.5 flex items-center justify-between gap-2">
                  <span
                    className={cn(
                      "truncate text-sm",
                      isTyping ? "text-primary" : c.unread_count ? "text-foreground" : "text-muted-foreground"
                    )}
                  >
                    {isTyping
                      ? "typing…"
                      : last
                        ? `${last.sender_id === meId ? "You: " : ""}${preview(last.body, 40)}`
                        : roleLabel(c.other_user.role)}
                  </span>
                  {c.unread_count > 0 && (
                    <span className="font-num flex h-5 min-w-[20px] shrink-0 items-center justify-center rounded-full bg-accent px-1.5 text-[11px] font-semibold text-accent-foreground">
                      {c.unread_count > 99 ? "99+" : c.unread_count}
                    </span>
                  )}
                </span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function PeopleResults({ results, searching, error, existingWith, onPick }) {
  if (error) return <p className="px-4 py-6 text-center text-sm text-status-fail">{error}</p>;

  if (results === null || (searching && results.length === 0)) {
    return <p className="px-4 py-8 text-center text-sm text-muted-foreground">Searching…</p>;
  }

  if (results.length === 0) {
    return <p className="px-4 py-8 text-center text-sm text-muted-foreground">No one matches that search.</p>;
  }

  // While a newer search is in flight the list on screen is out of date:
  // dim it and block clicks so nobody starts a chat with the wrong person.
  return (
    <ul
      className={cn("transition-opacity", searching && "pointer-events-none opacity-50")}
      aria-busy={searching}
    >
      {results.map((user) => (
        <li key={user.user_id}>
          <button
            type="button"
            onClick={() => onPick(user)}
            className="flex w-full items-center gap-3 border-b border-border/60 px-4 py-3 text-left hover:bg-muted"
            data-cursor-hover
          >
            <Avatar user={user} />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium">{user.name}</span>
              <span className="block truncate text-xs text-muted-foreground">
                {[roleLabel(user.role), user.laboratory_name].filter(Boolean).join(" · ")}
              </span>
            </span>
            <span className="shrink-0 text-xs font-medium text-primary">
              {existingWith.has(user.user_id) ? "Open chat" : "Start chat"}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function EmptyState({ notFound, onBack }) {
  return (
    <div className="flex h-full flex-1 flex-col items-center justify-center bg-muted/60 px-8 text-center">
      <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-rail text-rail-foreground">
        <Scale className="h-7 w-7" />
      </span>
      {notFound ? (
        <>
          <h2 className="mt-5 font-heading text-lg font-semibold">That conversation isn&apos;t available</h2>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            It may belong to another account, or no longer exist.
          </p>
          <button
            type="button"
            onClick={onBack}
            className="mt-4 rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:brightness-110"
            data-cursor-hover
          >
            Go to TeamDesk
          </button>
        </>
      ) : (
        <>
          <h2 className="mt-5 font-heading text-lg font-semibold">Talk to your team</h2>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            Pick a conversation on the left, or search for a colleague to start a new one. Messages arrive the
            moment they&apos;re sent.
          </p>
        </>
      )}
    </div>
  );
}
