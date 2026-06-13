import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  Message,
  loadConversationFromLocalStorage,
  saveConversationToLocalStorage,
  clearConversation as clearStoredConversation,
} from '@/lib/ariaStorage';

interface ARIAContextType {
  messages: Message[];
  conversationId: string | undefined;
  isLoading: boolean;
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  setConversationId: React.Dispatch<React.SetStateAction<string | undefined>>;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  clearARIAConversation: () => void;
}

const ARIAContext = createContext<ARIAContextType | undefined>(undefined);

export function ARIAProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [isLoading, setLoading] = useState<boolean>(false);

  // Initialize state from localStorage on load
  useEffect(() => {
    const stored = loadConversationFromLocalStorage();
    if (stored.messages.length > 0) {
      setMessages(stored.messages);
    }
    if (stored.conversationId) {
      setConversationId(stored.conversationId);
    }
  }, []);

  // Auto-save when messages or conversationId changes
  useEffect(() => {
    if (messages.length > 0 || conversationId) {
      saveConversationToLocalStorage(messages, conversationId);
    }
  }, [messages, conversationId]);

  const clearARIAConversation = () => {
    setMessages([]);
    setConversationId(undefined);
    setLoading(false);
    clearStoredConversation();
  };

  return (
    <ARIAContext.Provider
      value={{
        messages,
        conversationId,
        isLoading,
        setMessages,
        setConversationId,
        setLoading,
        clearARIAConversation,
      }}
    >
      {children}
    </ARIAContext.Provider>
  );
}

export function useARIA() {
  const context = useContext(ARIAContext);
  if (context === undefined) {
    throw new Error('useARIA must be used within an ARIAProvider');
  }
  return context;
}
