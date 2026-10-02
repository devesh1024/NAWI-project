import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from "react";
import { io } from "socket.io-client";
import { api, API_URL } from "@/lib/apiClient";
import { useAuth } from "@/hooks/useAuth";
import { preview } from "@/components/chat/chatUtils";

const ChatContext = createContext(null);

const MAX_TOASTS = 4;
const TOAST_MS = 8000;
const TYPING_EXPIRY_MS = 4000;

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const initialState = {
  loaded: false,
  conversations: {}, // conversation_id -> summary (other_user, last_message, unread_count…)
  threads: {}, // conversation_id -> { items, hasMore, loaded, loadingOlder }
  typing: {}, // conversation_id -> true while the other person is typing
  online: {}, // user_id -> true
};

const byTime = (a, b) =>
  new Date(a.created_at) - new Date(b.created_at) || String(a.message_id).localeCompare(String(b.message_id));

const emptyThread = { items: [], hasMore: false, loaded: false, loadingOlder: false };

function reducer(state, action) {
  switch (action.type) {
    case "CONVERSATIONS_LOADED": {
      const next = {};
      action.list.forEach((c) => {
        next[c.conversation_id] = c;
      });
      return { ...state, loaded: true, conversations: next };
    }

    case "CONVERSATION_UPSERT":
      return {
        ...state,
        conversations: { ...state.conversations, [action.conversation.conversation_id]: action.conversation },
      };

    case "UNREAD_CLEARED": {
      const c = state.conversations[action.cid];
      if (!c || c.unread_count === 0) return state;
      return { ...state, conversations: { ...state.conversations, [action.cid]: { ...c, unread_count: 0 } } };
    }

    case "THREAD_LOADED": {
      // Keep messages that are still waiting on the server; they are not in `items` yet.
      const pending = (state.threads[action.cid]?.items || []).filter((m) => m.status);
      const known = new Set(action.items.map((m) => m.message_id));
      const items = [...action.items, ...pending.filter((m) => !known.has(m.message_id))].sort(byTime);
      return {
        ...state,
        threads: {
          ...state.threads,
          [action.cid]: { items, hasMore: action.hasMore, loaded: true, loadingOlder: false },
        },
      };
    }

    case "OLDER_LOADING": {
      const t = state.threads[action.cid] || emptyThread;
      return { ...state, threads: { ...state.threads, [action.cid]: { ...t, loadingOlder: action.value } } };
    }

    case "OLDER_LOADED": {
      const t = state.threads[action.cid] || emptyThread;
      const known = new Set(t.items.map((m) => m.message_id));
      const items = [...action.items.filter((m) => !known.has(m.message_id)), ...t.items].sort(byTime);
      return {
        ...state,
        threads: { ...state.threads, [action.cid]: { ...t, items, hasMore: action.hasMore, loadingOlder: false } },
      };
    }

    case "MESSAGE_UPSERT": {
      // Only touch threads that are open/loaded; others are fetched fresh when opened.
      const t = state.threads[action.cid];
      if (!t || !t.loaded) return state;

      const { message, clientId } = action;
      let items = t.items;
      const existing = items.findIndex((m) => m.message_id === message.message_id);
      const optimistic = clientId ? items.findIndex((m) => m.client_id === clientId) : -1;

      if (existing >= 0) {
        items = items.map((m, i) => (i === existing ? { ...m, ...message } : m));
        if (optimistic >= 0 && optimistic !== existing) items = items.filter((_, i) => i !== optimistic);
      } else if (optimistic >= 0) {
        items = items.map((m, i) => (i === optimistic ? { ...message } : m));
      } else {
        items = [...items, message];
      }
      return { ...state, threads: { ...state.threads, [action.cid]: { ...t, items: items.sort(byTime) } } };
    }

    case "PENDING_ADD": {
      const t = state.threads[action.message.conversation_id] || emptyThread;
      return {
        ...state,
        threads: {
          ...state.threads,
          [action.message.conversation_id]: { ...t, items: [...t.items, action.message].sort(byTime) },
        },
      };
    }

    case "PENDING_UPDATE": {
      const t = state.threads[action.cid];
      if (!t) return state;
      const items = t.items.map((m) => (m.client_id === action.clientId ? { ...m, ...action.patch } : m));
      return { ...state, threads: { ...state.threads, [action.cid]: { ...t, items } } };
    }

    case "PENDING_REMOVE": {
      const t = state.threads[action.cid];
      if (!t) return state;
      const items = t.items.filter((m) => m.client_id !== action.clientId);
      return { ...state, threads: { ...state.threads, [action.cid]: { ...t, items } } };
    }

    case "MESSAGES_READ": {
      // Either the other person read my messages, or I read theirs: stamp read_at.
      const t = state.threads[action.cid];
      if (!t) return state;
      const ids = new Set(action.ids);
      const stamp = new Date().toISOString();
      const items = t.items.map((m) => (ids.has(m.message_id) ? { ...m, read_at: m.read_at || stamp } : m));
      return { ...state, threads: { ...state.threads, [action.cid]: { ...t, items } } };
    }

    case "TYPING":
      return { ...state, typing: { ...state.typing, [action.cid]: action.value } };

    case "PRESENCE": {
      const online = { ...state.online };
      if (action.online) online[action.userId] = true;
      else delete online[action.userId];
      return { ...state, online };
    }

    case "PRESENCE_SET": {
      const online = { ...state.online };
      action.queried.forEach((id) => delete online[id]);
      action.online.forEach((id) => {
        online[id] = true;
      });
      return { ...state, online };
    }

    default:
      return state;
  }
}

const newClientId = () =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------
export function ChatProvider({ children }) {
  const { token, signOut } = useAuth();
  const [state, dispatch] = useReducer(reducer, initialState);
  const [me, setMe] = useState(null);
  const [status, setStatus] = useState("connecting"); // connecting | online | offline
  const [toasts, setToasts] = useState([]);
  const [activeId, setActiveId] = useState(null);

  const socketRef = useRef(null);
  const meRef = useRef(null);
  const activeRef = useRef(null);
  const stateRef = useRef(state);
  const typingTimers = useRef({});
  const toastTimers = useRef({});
  const everConnected = useRef(false);

  stateRef.current = state;
  meRef.current = me;
  activeRef.current = activeId;

  // ----- toasts ------------------------------------------------------------
  const dismissToast = useCallback((id) => {
    clearTimeout(toastTimers.current[id]);
    delete toastTimers.current[id];
    setToasts((list) => list.filter((t) => t.id !== id));
  }, []);

  const pushToast = useCallback(
    (toast) => {
      const id = newClientId();
      setToasts((list) => [{ id, ...toast }, ...list].slice(0, MAX_TOASTS));
      toastTimers.current[id] = setTimeout(() => dismissToast(id), TOAST_MS);
    },
    [dismissToast]
  );

  // ----- data loading -----------------------------------------------------
  const refreshConversations = useCallback(async () => {
    if (!token) return;
    try {
      const list = await api.listConversations(token);
      dispatch({ type: "CONVERSATIONS_LOADED", list });
    } catch (err) {
      console.error("TeamDesk: could not load conversations", err);
    }
  }, [token]);

  const loadMessages = useCallback(
    async (cid) => {
      if (!token) return;
      try {
        const page = await api.listChatMessages(cid, {}, token);
        dispatch({ type: "THREAD_LOADED", cid, items: page.messages, hasMore: page.has_more });
      } catch (err) {
        console.error("TeamDesk: could not load messages", err);
      }
    },
    [token]
  );

  const loadOlder = useCallback(
    async (cid) => {
      const thread = stateRef.current.threads[cid];
      const oldest = thread?.items.find((m) => !m.status);
      if (!token || !thread || thread.loadingOlder || !thread.hasMore || !oldest) return;
      dispatch({ type: "OLDER_LOADING", cid, value: true });
      try {
        const page = await api.listChatMessages(cid, { before: oldest.created_at }, token);
        dispatch({ type: "OLDER_LOADED", cid, items: page.messages, hasMore: page.has_more });
      } catch (err) {
        dispatch({ type: "OLDER_LOADING", cid, value: false });
      }
    },
    [token]
  );

  // ----- read receipts ------------------------------------------------------
  const markRead = useCallback(
    (cid) => {
      const conversation = stateRef.current.conversations[cid];
      const thread = stateRef.current.threads[cid];
      const hasUnreadLocal =
        (conversation?.unread_count || 0) > 0 ||
        (thread?.items || []).some((m) => m.sender_id !== meRef.current?.user_id && !m.read_at && !m.status);
      if (!hasUnreadLocal) return;

      dispatch({ type: "UNREAD_CLEARED", cid });
      const mine = meRef.current?.user_id;
      const ids = (thread?.items || []).filter((m) => m.sender_id !== mine && !m.read_at).map((m) => m.message_id);
      if (ids.length) dispatch({ type: "MESSAGES_READ", cid, ids });

      const socket = socketRef.current;
      if (socket?.connected) {
        socket.emit("message:read", { conversation_id: cid });
      } else {
        api.markConversationRead(cid, token).catch(() => {});
      }
    },
    [token]
  );

  const viewing = (cid) =>
    activeRef.current === cid && document.visibilityState === "visible" && document.hasFocus();

  // ----- sending ------------------------------------------------------------
  const deliver = useCallback(
    (cid, body, clientId) => {
      const settle = (message) => {
        dispatch({ type: "MESSAGE_UPSERT", cid, message, clientId });
      };
      const fail = (error) =>
        dispatch({ type: "PENDING_UPDATE", cid, clientId, patch: { status: "failed", error } });

      const socket = socketRef.current;

      if (socket?.connected) {
        socket.timeout(8000).emit("message:send", { conversation_id: cid, body, client_id: clientId }, (err, res) => {
          if (err) return fail("No response from the server");
          if (!res?.ok) return fail(res?.error || "Message could not be sent");
          settle(res.message);
        });
        return;
      }

      // Socket is down: fall back to plain HTTP so the message still goes out.
      api
        .sendChatMessage(cid, body, token)
        .then(settle)
        .catch((e) => fail(e.message));
    },
    [token]
  );

  const sendMessage = useCallback(
    (cid, body) => {
      const text = (body || "").trim();
      if (!text || !meRef.current) return;
      const clientId = newClientId();

      dispatch({
        type: "PENDING_ADD",
        message: {
          message_id: `local-${clientId}`,
          client_id: clientId,
          conversation_id: cid,
          sender_id: meRef.current.user_id,
          body: text,
          created_at: new Date().toISOString(),
          read_at: null,
          status: "sending",
        },
      });
      deliver(cid, text, clientId);
    },
    [deliver]
  );

  const retryMessage = useCallback(
    (cid, clientId) => {
      const failed = stateRef.current.threads[cid]?.items.find((m) => m.client_id === clientId);
      if (!failed) return;
      dispatch({ type: "PENDING_UPDATE", cid, clientId, patch: { status: "sending", error: null } });
      deliver(cid, failed.body, clientId);
    },
    [deliver]
  );

  const sendTyping = useCallback((cid, isTyping) => {
    const socket = socketRef.current;
    if (socket?.connected) socket.emit("typing", { conversation_id: cid, is_typing: isTyping });
  }, []);

  const openConversationWith = useCallback(
    async (userId) => {
      const conversation = await api.openConversation(userId, token);
      dispatch({ type: "CONVERSATION_UPSERT", conversation });
      return conversation.conversation_id;
    },
    [token]
  );

  // ----- realtime events ------------------------------------------------------
  const handleIncoming = useCallback(
    ({ message, conversation, client_id: clientId }) => {
      const mine = meRef.current?.user_id;
      const cid = message.conversation_id;

      dispatch({ type: "CONVERSATION_UPSERT", conversation });
      dispatch({ type: "MESSAGE_UPSERT", cid, message, clientId });

      // The open chat is still fetching its history: refetch so this message isn't lost.
      if (activeRef.current === cid && !stateRef.current.threads[cid]?.loaded) loadMessages(cid);

      if (message.sender_id === mine) return;

      // The sender stopped typing the moment the message landed.
      dispatch({ type: "TYPING", cid, value: false });

      if (viewing(cid)) {
        // Already looking at this chat: no card needed, just mark it read.
        socketRef.current?.emit("message:read", { conversation_id: cid });
        dispatch({ type: "UNREAD_CLEARED", cid });
        dispatch({ type: "MESSAGES_READ", cid, ids: [message.message_id] });
        return;
      }

      pushToast({
        conversation_id: cid,
        title: conversation.other_user.name,
        body: preview(message.body),
      });
    },
    [pushToast, loadMessages]
  );

  // Profile + conversation list once we have a token.
  useEffect(() => {
    if (!token) return undefined;
    let cancelled = false;

    api
      .getMyProfile(token)
      .then((profile) => {
        if (cancelled) return;
        setMe({
          user_id: String(profile.user_id),
          name: [profile.first_name, profile.last_name].filter(Boolean).join(" ") || profile.email,
          email: profile.email,
          role: profile.role,
        });
      })
      .catch((err) => console.error("TeamDesk: could not load profile", err));

    refreshConversations();
    return () => {
      cancelled = true;
    };
  }, [token, refreshConversations]);

  // The socket itself.
  useEffect(() => {
    if (!token || !API_URL) {
      setStatus("offline");
      return undefined;
    }

    const socket = io(API_URL, {
      path: "/socket.io",
      auth: { token },
      transports: ["websocket", "polling"],
      reconnectionDelayMax: 5000,
    });
    socketRef.current = socket;
    setStatus("connecting");

    socket.on("connect", () => {
      setStatus("online");
      // After a drop, catch up on anything missed while we were away.
      if (everConnected.current) {
        refreshConversations();
        const open = activeRef.current;
        if (open) loadMessages(open);
      }
      everConnected.current = true;
    });
    socket.on("disconnect", () => setStatus("offline"));
    socket.on("connect_error", (err) => {
      setStatus("offline");
      if (err?.message === "unauthorized") signOut(); // token expired or account disabled
    });
    socket.on("auth:expired", () => signOut());

    socket.on("message:new", handleIncoming);

    socket.on("message:read", ({ conversation_id: cid, message_ids: ids }) => {
      dispatch({ type: "MESSAGES_READ", cid, ids });
    });

    socket.on("typing", ({ conversation_id: cid, is_typing: isTyping }) => {
      clearTimeout(typingTimers.current[cid]);
      dispatch({ type: "TYPING", cid, value: !!isTyping });
      if (isTyping) {
        // If the "stopped typing" event is lost, don't leave the indicator stuck.
        typingTimers.current[cid] = setTimeout(
          () => dispatch({ type: "TYPING", cid, value: false }),
          TYPING_EXPIRY_MS
        );
      }
    });

    socket.on("presence", ({ user_id: userId, online }) => dispatch({ type: "PRESENCE", userId, online }));

    return () => {
      socket.removeAllListeners();
      socket.disconnect();
      socketRef.current = null;
    };
    // handleIncoming / refreshConversations are stable for a given token
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // Ask who is online whenever the set of chat partners (or the connection) changes.
  const partnerKey = Object.values(state.conversations)
    .map((c) => c.other_user.user_id)
    .sort()
    .join(",");

  useEffect(() => {
    const socket = socketRef.current;
    if (status !== "online" || !socket || !partnerKey) return;
    const ids = partnerKey.split(",");
    socket.emit("presence:query", { user_ids: ids }, (res) => {
      dispatch({ type: "PRESENCE_SET", queried: ids, online: res?.online || [] });
    });
  }, [status, partnerKey]);

  // Returning to the tab while a chat is open counts as reading it.
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === "visible" && activeRef.current) markRead(activeRef.current);
    };
    window.addEventListener("focus", onVisible);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.removeEventListener("focus", onVisible);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [markRead]);

  // ----- derived ------------------------------------------------------------------
  const conversations = useMemo(
    () =>
      Object.values(state.conversations).sort(
        (a, b) => new Date(b.last_message_at || 0) - new Date(a.last_message_at || 0)
      ),
    [state.conversations]
  );

  const unreadTotal = useMemo(
    () => conversations.reduce((sum, c) => sum + (c.unread_count || 0), 0),
    [conversations]
  );

  const notifications = useMemo(() => conversations.filter((c) => c.unread_count > 0), [conversations]);

  // Unread count in the tab title, e.g. "(2) NAWI TestSuite".
  useEffect(() => {
    const base = document.title.replace(/^\(\d+\)\s*/, "");
    document.title = unreadTotal > 0 ? `(${unreadTotal}) ${base}` : base;
    return () => {
      document.title = base;
    };
  }, [unreadTotal]);

  useEffect(
    () => () => {
      Object.values(toastTimers.current).forEach(clearTimeout);
      Object.values(typingTimers.current).forEach(clearTimeout);
    },
    []
  );

  const value = {
    me,
    status,
    loaded: state.loaded,
    conversations,
    threads: state.threads,
    typing: state.typing,
    online: state.online,
    unreadTotal,
    notifications,
    toasts,
    activeId,
    setActiveConversation: setActiveId,
    dismissToast,
    loadMessages,
    loadOlder,
    markRead,
    sendMessage,
    retryMessage,
    sendTyping,
    openConversationWith,
    refreshConversations,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat must be used within ChatProvider");
  return ctx;
}
