export interface Message {
  role: 'user' | 'aria';
  content: string;
  thinkingMessage?: string;
  thinkingIcon?: 'brain' | 'lock' | 'heart' | 'target' | 'lightbulb' | 'sparkle';
  type?: string;
  crisis_detected?: boolean;
  crisis_severity?: string | number;
  resources?: any[];
  encourage?: string;
  contact_emergency?: string;
}

export interface StoredConversation {
  messages: Message[];
  conversationId?: string;
}

const STORAGE_KEY = 'mc_aria_conversation';

export function saveConversationToLocalStorage(messages: Message[], conversationId?: string) {
  try {
    const data: StoredConversation = { messages, conversationId };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (error) {
    console.error('Failed to save ARIA conversation to localStorage:', error);
  }
}

export function loadConversationFromLocalStorage(): StoredConversation {
  try {
    const dataStr = localStorage.getItem(STORAGE_KEY);
    if (dataStr) {
      return JSON.parse(dataStr);
    }
  } catch (error) {
    console.error('Failed to load ARIA conversation from localStorage:', error);
  }
  return { messages: [] };
}

export function clearConversation() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.error('Failed to clear ARIA conversation from localStorage:', error);
  }
}
