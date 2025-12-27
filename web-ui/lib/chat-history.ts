/**
 * Chat History Persistence Service
 * 
 * Saves/loads chat history to/from localStorage
 * Restores conversation on page refresh
 */

interface ChatMessage {
    id: string;
    type: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: Date;
    isStreaming?: boolean;
    agent?: string;
    metadata?: any;
}

const STORAGE_KEY = 'thesis_chat_history';
const WORKSPACE_KEY = 'thesis_current_workspace';

export class ChatHistoryService {
    /**
     * Save chat messages to localStorage
     */
    static saveChatHistory(workspaceId: string, messages: ChatMessage[]): void {
        try {
            const history = {
                workspaceId,
                messages: messages.map(msg => ({
                    ...msg,
                    timestamp: msg.timestamp.toISOString() // Convert Date tostring
                })),
                lastUpdated: new Date().toISOString()
            };

            localStorage.setItem(`${STORAGE_KEY}_${workspaceId}`, JSON.stringify(history));
            localStorage.setItem(WORKSPACE_KEY, workspaceId);
        } catch (error) {
            console.error('Failed to save chat history:', error);
        }
    }

    /**
     * Load chat history from localStorage
     */
    static loadChatHistory(workspaceId: string): ChatMessage[] {
        try {
            const stored = localStorage.getItem(`${STORAGE_KEY}_${workspaceId}`);
            if (!stored) return [];

            const history = JSON.parse(stored);

            // Convert timestamp strings back to Date objects
            return history.messages.map((msg: any) => ({
                ...msg,
                timestamp: new Date(msg.timestamp)
            }));
        } catch (error) {
            console.error('Failed to load chat history:', error);
            return [];
        }
    }

    /**
     * Get last used workspace ID
     */
    static getLastWorkspace(): string | null {
        return localStorage.getItem(WORKSPACE_KEY);
    }

    /**
     * Clear chat history for workspace
     */
    static clearHistory(workspaceId: string): void {
        localStorage.removeItem(`${STORAGE_KEY}_${workspaceId}`);
    }

    /**
     * Clear all chat histories
     */
    static clearAll(): void {
        Object.keys(localStorage)
            .filter(key => key.startsWith(STORAGE_KEY))
            .forEach(key => localStorage.removeItem(key));
        localStorage.removeItem(WORKSPACE_KEY);
    }

    /**
     * Export chat history as JSON file
     */
    static exportHistory(workspaceId: string): void {
        const messages = this.loadChatHistory(workspaceId);
        const blob = new Blob([JSON.stringify(messages, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chat-history-${workspaceId}-${new Date().toISOString()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    /**
     * Get statistics about chat history
     */
    static getStats(workspaceId: string): {
        messageCount: number;
        userMessages: number;
        assistantMessages: number;
        lastUpdated: string | null;
    } {
        const messages = this.loadChatHistory(workspaceId);

        return {
            messageCount: messages.length,
            userMessages: messages.filter(m => m.type === 'user').length,
            assistantMessages: messages.filter(m => m.type === 'assistant').length,
            lastUpdated: messages.length > 0 ? messages[messages.length - 1].timestamp.toISOString() : null
        };
    }
}
