import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { ArrowDown, ArrowLeft, SendHorizonal, WifiOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { useChat } from "@/hooks/useChat";
import { Avatar } from "./Avatar";
import { MessageBubble } from "./MessageBubble";
import { dayKey, dayLabel, roleLabel } from "./chatUtils";

const MAX_LENGTH = 2000;

// A faint measuring grid behind the conversation, in the theme's border colour.
const GRID = {
  backgroundImage:
    "linear-gradient(hsl(var(--border) / 0.55) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--border) / 0.55) 1px, transparent 1px)",
  backgroundSize: "28px 28px",
};

export function ChatPane({ conversation, drafts, onBack }) {
  const {
    me,
    status,
    threads,
    typing,
    online,
    loadMessages,
    loadOlder,
    markRead,
    sendMessage,
    retryMessage,
    sendTyping,
  } = useChat();

  const cid = conversation.conversation_id;
  const other = conversation.other_user;
  const thread = threads[cid];
  const items = thread?.items ?? [];
  const isOnline = !!online[other.user_id];
  const otherTyping = !!typing[cid];

  const scrollRef = useRef(null);
  const atBottom = useRef(true);
  const savedHeight = useRef(0);
  const lastId = useRef(null);
  const firstId = useRef(null);
  const [newBelow, setNewBelow] = useState(0);

  // ---- open: fetch history ----------------------------------------------
  useEffect(() => {
    loadMessages(cid);
  }, [cid, loadMessages]);

  // ---- reading: mark the other person's messages read while this chat is in view
  useEffect(() => {
    if (!thread?.loaded) return;
    if (document.visibilityState === "visible" && document.hasFocus()) markRead(cid);
  }, [cid, thread?.loaded, items.length, conversation.unread_count, markRead]);

  // ---- scrolling ------------------------------------------------------------
  const scrollToBottom = (smooth) => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: smooth ? "smooth" : "auto" });
  };

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el || !thread?.loaded) return;

    const last = items[items.length - 1];
    const first = items[0];
    const lastNow = last?.message_id ?? null;
    const firstNow = first?.message_id ?? null;

    if (lastId.current === null) {
      scrollToBottom(false); // first paint of this conversation
    } else if (lastNow !== lastId.current) {
      // something arrived at the bottom
      const mine = last.sender_id === me?.user_id;
      if (mine || atBottom.current) scrollToBottom(true);
      else setNewBelow((n) => n + 1);
    } else if (firstNow !== firstId.current && savedHeight.current) {
      // older messages were added above: keep the viewport where it was
      el.scrollTop += el.scrollHeight - savedHeight.current;
    }

    savedHeight.current = 0;
    lastId.current = lastNow;
    firstId.current = firstNow;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, thread?.loaded]);

  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    atBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    if (atBottom.current && newBelow) setNewBelow(0);

    if (el.scrollTop < 60 && thread?.hasMore && !thread.loadingOlder) {
      savedHeight.current = el.scrollHeight;
      loadOlder(cid);
    }
  };

  // ---- composer ---------------------------------------------------------------
  const [text, setText] = useState(drafts.current[cid] || "");
  const areaRef = useRef(null);
  const typingState = useRef({ active: false, timer: null });

  const stopTyping = () => {
    clearTimeout(typingState.current.timer);
    if (typingState.current.active) {
      typingState.current.active = false;
      sendTyping(cid, false);
    }
  };

  useEffect(() => () => stopTyping(), []); // eslint-disable-line react-hooks/exhaustive-deps

  const resize = () => {
    const area = areaRef.current;
    if (!area) return;
    area.style.height = "auto";
    area.style.height = `${Math.min(area.scrollHeight, 128)}px`;
  };

  useEffect(resize, [text]);

  const onChange = (e) => {
    const value = e.target.value;
    setText(value);
    drafts.current[cid] = value;

    if (!value.trim()) return stopTyping();
    if (!typingState.current.active) {
      typingState.current.active = true;
      sendTyping(cid, true);
    }
    clearTimeout(typingState.current.timer);
    typingState.current.timer = setTimeout(stopTyping, 2000);
  };

  const submit = () => {
    const value = text.trim();
    if (!value) return;
    sendMessage(cid, value);
    setText("");
    drafts.current[cid] = "";
    stopTyping();
    atBottom.current = true;
    areaRef.current?.focus();
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  // ---- render ---------------------------------------------------------------------
  const subtitle = otherTyping
    ? "typing…"
    : isOnline
      ? "Online"
      : [roleLabel(other.role), other.laboratory_name].filter(Boolean).join(" · ");

  let previousDay = null;
  let previousSender = null;

  return (
    <section className="flex h-full min-w-0 flex-1 flex-col" aria-label={`Conversation with ${other.name}`}>
      <header className="flex items-center gap-3 border-b border-border bg-surface px-4 py-3">
        <button
          type="button"
          onClick={onBack}
          className="-ml-1 rounded-lg p-2 hover:bg-muted md:hidden"
          aria-label="Back to conversations"
          data-cursor-hover
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <Avatar user={other} online={isOnline} />
        <div className="min-w-0">
          <h2 className="truncate font-heading text-base font-semibold leading-tight">{other.name}</h2>
          <p
            className={cn(
              "truncate text-xs leading-tight",
              otherTyping || isOnline ? "text-primary" : "text-muted-foreground"
            )}
          >
            {subtitle}
          </p>
          {(otherTyping || isOnline) && (
            <p className="sr-only">
              {roleLabel(other.role)}
              {other.laboratory_name ? `, ${other.laboratory_name}` : ""}
            </p>
          )}
        </div>
      </header>

      {status === "offline" && (
        <div className="flex items-center justify-center gap-2 bg-accent/20 px-4 py-1.5 text-xs text-foreground" role="status">
          <WifiOff className="h-3.5 w-3.5" /> Connection lost. Reconnecting; messages will still be sent.
        </div>
      )}

      <div className="relative min-h-0 flex-1 bg-muted/60" style={GRID}>
        <div ref={scrollRef} onScroll={onScroll} className="h-full overflow-y-auto px-4 py-4 md:px-8">
          {thread?.loadingOlder && (
            <p className="pb-3 text-center text-xs text-muted-foreground">Loading earlier messages…</p>
          )}

          {!thread?.loaded && <p className="py-10 text-center text-sm text-muted-foreground">Loading messages…</p>}

          {thread?.loaded && items.length === 0 && (
            <p className="mx-auto mt-10 max-w-xs rounded-xl border border-border bg-surface px-4 py-3 text-center text-sm text-muted-foreground">
              No messages yet. Say hello to {other.name.split(" ")[0]}.
            </p>
          )}

          {items.map((message, index) => {
            const key = dayKey(message.created_at);
            const newDay = key !== previousDay;
            const grouped = !newDay && previousSender === message.sender_id;
            previousDay = key;
            previousSender = message.sender_id;

            const next = items[index + 1];
            const endOfGroup =
              !next || next.sender_id !== message.sender_id || dayKey(next.created_at) !== key;

            return (
              <React.Fragment key={message.message_id}>
                {newDay && (
                  <div className="my-3 flex justify-center">
                    <span className="rounded-full border border-border bg-surface px-3 py-1 text-xs text-muted-foreground">
                      {dayLabel(message.created_at)}
                    </span>
                  </div>
                )}
                <div className={grouped ? "mt-0.5" : "mt-3"}>
                  <MessageBubble
                    message={message}
                    mine={message.sender_id === me?.user_id}
                    endOfGroup={endOfGroup}
                    onRetry={() => retryMessage(cid, message.client_id)}
                  />
                </div>
              </React.Fragment>
            );
          })}

          {otherTyping && (
            <p className="mt-3 text-xs text-muted-foreground" aria-hidden="true">
              {other.name.split(" ")[0]} is typing…
            </p>
          )}
        </div>

        {newBelow > 0 && (
          <button
            type="button"
            onClick={() => {
              scrollToBottom(true);
              setNewBelow(0);
            }}
            className="absolute bottom-3 left-1/2 flex -translate-x-1/2 items-center gap-1.5 rounded-full bg-primary px-3.5 py-1.5 text-xs font-medium text-primary-foreground shadow-raised"
            data-cursor-hover
          >
            <ArrowDown className="h-3.5 w-3.5" />
            {newBelow} new {newBelow === 1 ? "message" : "messages"}
          </button>
        )}
      </div>

      <div className="border-t border-border bg-surface px-4 py-3">
        <div className="flex items-end gap-2">
          <textarea
            ref={areaRef}
            value={text}
            onChange={onChange}
            onKeyDown={onKeyDown}
            rows={1}
            maxLength={MAX_LENGTH}
            placeholder={`Message ${other.name.split(" ")[0]}`}
            aria-label="Type a message"
            className="max-h-32 min-h-[44px] flex-1 resize-none rounded-xl border border-input bg-background px-4 py-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <button
            type="button"
            onClick={submit}
            disabled={!text.trim()}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-soft transition hover:brightness-110 disabled:opacity-40"
            aria-label="Send message"
            data-cursor-hover
          >
            <SendHorizonal className="h-5 w-5" />
          </button>
        </div>
        <p className="mt-1.5 flex justify-between px-1 text-[11px] text-muted-foreground">
          <span>Enter to send · Shift+Enter for a new line</span>
          {text.length > MAX_LENGTH - 200 && (
            <span className="font-num">
              {text.length}/{MAX_LENGTH}
            </span>
          )}
        </p>
      </div>
    </section>
  );
}
