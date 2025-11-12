// D-Bus client for communicating with henzai daemon

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

const DBUS_NAME = 'org.gnome.henzai';
const DBUS_PATH = '/org/gnome/henzai';

const henzaiInterface = `
<node>
    <interface name="org.gnome.henzai">
        <method name="SendMessage">
            <arg type="s" direction="in" name="message"/>
            <arg type="s" direction="out" name="response"/>
        </method>
        <method name="SendMessageStreaming">
            <arg type="s" direction="in" name="message"/>
            <arg type="s" direction="out" name="generation_id"/>
        </method>
        <method name="StopGeneration">
            <arg type="b" direction="out" name="success"/>
        </method>
        <method name="GetStatus">
            <arg type="s" direction="out" name="status"/>
        </method>
        <method name="ClearHistory"/>
        <method name="NewConversation">
            <arg type="s" direction="out" name="status"/>
        </method>
        <method name="ListModels">
            <arg type="s" direction="out" name="models_json"/>
        </method>
        <method name="SetModel">
            <arg type="s" direction="in" name="model_id"/>
            <arg type="s" direction="out" name="status"/>
        </method>
        <method name="GetCurrentModel">
            <arg type="s" direction="out" name="model_id"/>
        </method>
        <method name="SupportsReasoning">
            <arg type="b" direction="out" name="supported"/>
        </method>
        <method name="GetReasoningEnabled">
            <arg type="b" direction="out" name="enabled"/>
        </method>
        <method name="SetReasoningEnabled">
            <arg type="b" direction="in" name="enabled"/>
            <arg type="s" direction="out" name="status"/>
        </method>
        <method name="ListSessions">
            <arg type="i" direction="in" name="limit"/>
            <arg type="s" direction="out" name="sessions_json"/>
        </method>
        <method name="LoadSession">
            <arg type="i" direction="in" name="session_id"/>
            <arg type="s" direction="out" name="context_json"/>
        </method>
        <method name="DeleteSession">
            <arg type="i" direction="in" name="session_id"/>
            <arg type="s" direction="out" name="status"/>
        </method>
        <signal name="ResponseChunk">
            <arg type="s" name="generation_id"/>
            <arg type="s" name="chunk"/>
        </signal>
        <signal name="ThinkingChunk">
            <arg type="s" name="generation_id"/>
            <arg type="s" name="chunk"/>
        </signal>
        <signal name="StreamingComplete">
            <arg type="s" name="generation_id"/>
        </signal>
        <signal name="ModelChanged">
            <arg type="s" name="model_id"/>
        </signal>
        <signal name="ReasoningChanged">
            <arg type="b" name="enabled"/>
        </signal>
        <signal name="HistoryCleared"/>
    </interface>
</node>
`;

const henzaiProxy = Gio.DBusProxy.makeProxyWrapper(henzaiInterface);

/**
 * D-Bus client for henzai daemon
 */
export class DaemonClient {
    constructor() {
        this._proxy = null;
        this._connecting = false;
        this._chunkCallback = null;  // Callback for streaming chunks
        this._signalId = null;  // Signal connection ID
        this._currentGenerationId = null;  // Track current generation
        this._initProxy();
    }

    /**
     * Initialize the D-Bus proxy connection
     */
    _initProxy() {
        if (this._connecting) {
            return;
        }

        this._connecting = true;

        try {
            this._proxy = new henzaiProxy(
                Gio.DBus.session,
                DBUS_NAME,
                DBUS_PATH,
                (proxy, error) => {
                    this._connecting = false;

                    if (error) {
                        console.error('henzai: Error connecting to daemon:', error);
                        this._proxy = null;
                    } else {
                        // CRITICAL: Set timeout to infinite for long-running operations
                        // The default timeout is 25 seconds, but reasoning can take minutes
                        this._proxy.g_default_timeout = -1;  // -1 = no timeout
                        console.log('henzai: Connected to daemon (timeout: infinite)');
                    }
                }
            );
        } catch (error) {
            console.error('henzai: Error creating proxy:', error);
            this._connecting = false;
            this._proxy = null;
        }
    }

    /**
     * Check if connected to daemon
     */
    isConnected() {
        return this._proxy !== null;
    }

    /**
     * Send a message to the AI assistant
     * @param {string} message - User's message
     * @returns {Promise<string>} - AI's response
     */
    async sendMessage(message) {
        if (!this.isConnected()) {
            throw new Error('Not connected to henzai daemon. Is it running?');
        }

        try {
            const [response] = await this._proxy.SendMessageAsync(message);
            return response;
        } catch (error) {
            console.error('henzai: Error sending message:', error);
            throw new Error(`Failed to send message: ${error.message}`);
        }
    }

    /**
     * Send a message with streaming response
     * @param {string} message - User's message
     * @param {function} onChunk - Callback for each chunk
     * @returns {Promise<string>} Generation ID
     */
    async sendMessageStreaming(message, onChunk) {
        if (!this.isConnected()) {
            throw new Error('Not connected to henzai daemon. Is it running?');
        }

        // Set up chunk callback - DON'T clear it after method returns
        // because chunks arrive AFTER the method returns (background threading)
        this._chunkCallback = onChunk;

        // Connect to ResponseChunk signal if not already connected
        if (!this._signalId) {
            this._signalId = this._proxy.connectSignal('ResponseChunk', (proxy, sender, [generationId, chunk]) => {
                console.log(`henzai: Received ResponseChunk signal for ${generationId}`);
                // Only process chunks for current generation
                if (generationId === this._currentGenerationId && this._chunkCallback) {
                    this._chunkCallback(chunk);
                } else if (generationId !== this._currentGenerationId) {
                    console.log(`henzai: Ignoring chunk from old generation: ${generationId} (current: ${this._currentGenerationId})`);
                } else {
                    console.warn('henzai: Received chunk but no callback set!');
                }
            });
            console.log('henzai: Connected to ResponseChunk signal');
        }

        try {
            // Start streaming with no timeout (reasoning can take minutes)
            // The method returns generation ID immediately, chunks arrive via signals
            const result = await new Promise((resolve, reject) => {
                this._proxy.call(
                    'SendMessageStreaming',
                    new GLib.Variant('(s)', [message]),
                    Gio.DBusCallFlags.NONE,
                    -1,  // timeout in milliseconds, -1 = no timeout
                    null,  // cancellable
                    (proxy, asyncResult) => {
                        try {
                            const returnValue = proxy.call_finish(asyncResult);
                            resolve(returnValue.deep_unpack());
                        } catch (e) {
                            reject(e);
                        }
                    }
                );
            });
            
            const [generationId] = result;
            this._currentGenerationId = generationId;
            console.log(`henzai: SendMessageStreaming returned generation ID: ${generationId}`);
            
            // NOTE: Don't clear callback here! Chunks arrive AFTER method returns.
            // The callback should be cleared when generation is done or stopped.
            
            return generationId;
        } catch (error) {
            this._chunkCallback = null;
            this._currentGenerationId = null;
            console.error('henzai: Error in streaming message:', error);
            throw new Error(`Failed to send streaming message: ${error.message}`);
        }
    }

    /**
     * Stop the current generation
     * @returns {Promise<boolean>}
     */
    async stopGeneration() {
        if (!this.isConnected()) {
            return false;
        }

        try {
            const [success] = await this._proxy.StopGenerationAsync();
            return success;
        } catch (error) {
            console.error('henzai: Error stopping generation:', error);
            return false;
        }
    }

    /**
     * Get daemon status
     * @returns {Promise<string>} - Status string
     */
    async getStatus() {
        if (!this.isConnected()) {
            return 'disconnected';
        }

        try {
            const [status] = await this._proxy.GetStatusAsync();
            return status;
        } catch (error) {
            console.error('henzai: Error getting status:', error);
            return 'error';
        }
    }

    /**
     * Clear conversation history
     */
    async clearHistory() {
        if (!this.isConnected()) {
            throw new Error('Not connected to daemon');
        }

        try {
            await this._proxy.ClearHistoryAsync();
        } catch (error) {
            console.error('henzai: Error clearing history:', error);
            throw new Error(`Failed to clear history: ${error.message}`);
        }
    }

    /**
     * Start a new conversation
     * @returns {Promise<string>} Status message
     */
    async newConversation() {
        if (!this.isConnected()) {
            throw new Error('Not connected to daemon');
        }

        try {
            const [status] = await this._proxy.NewConversationAsync();
            return status;
        } catch (error) {
            console.error('henzai: Error starting new conversation:', error);
            throw new Error(`Failed to start new conversation: ${error.message}`);
        }
    }

    /**
     * List all saved chat sessions
     * @param {number} limit - Maximum number of sessions
     * @returns {Promise<string>} JSON string of sessions
     */
    async listSessions(limit = 50) {
        if (!this.isConnected()) {
            throw new Error('Not connected to daemon');
        }

        try {
            const [sessionsJson] = await this._proxy.ListSessionsAsync(limit);
            return sessionsJson;
        } catch (error) {
            console.error('henzai: Error listing sessions:', error);
            throw new Error(`Failed to list sessions: ${error.message}`);
        }
    }

    /**
     * Load a previous chat session
     * @param {number} sessionId - ID of session to load
     * @returns {Promise<string>} JSON string of conversation history
     */
    async loadSession(sessionId) {
        if (!this.isConnected()) {
            throw new Error('Not connected to daemon');
        }

        try {
            const [contextJson] = await this._proxy.LoadSessionAsync(sessionId);
            return contextJson;
        } catch (error) {
            console.error('henzai: Error loading session:', error);
            throw new Error(`Failed to load session: ${error.message}`);
        }
    }

    /**
     * Delete a chat session
     * @param {number} sessionId - ID of session to delete
     * @returns {Promise<string>} Status message
     */
    async deleteSession(sessionId) {
        if (!this.isConnected()) {
            throw new Error('Not connected to daemon');
        }

        try {
            const [status] = await this._proxy.DeleteSessionAsync(sessionId);
            return status;
        } catch (error) {
            console.error('henzai: Error deleting session:', error);
            throw new Error(`Failed to delete session: ${error.message}`);
        }
    }

    /**
     * Check if current model supports reasoning
     * @returns {Promise<boolean>}
     */
    async supportsReasoning() {
        if (!this.isConnected()) {
            return false;
        }

        try {
            const [supported] = await this._proxy.SupportsReasoningAsync();
            return supported;
        } catch (error) {
            console.error('henzai: Error checking reasoning support:', error);
            return false;
        }
    }

    /**
     * Get reasoning enabled status
     * @returns {Promise<boolean>}
     */
    async getReasoningEnabled() {
        if (!this.isConnected()) {
            return false;
        }

        try {
            const [enabled] = await this._proxy.GetReasoningEnabledAsync();
            return enabled;
        } catch (error) {
            console.error('henzai: Error getting reasoning status:', error);
            return false;
        }
    }

    /**
     * Set reasoning enabled status
     * @param {boolean} enabled - Whether to enable reasoning
     * @returns {Promise<string>} Status message
     */
    async setReasoningEnabled(enabled) {
        if (!this.isConnected()) {
            throw new Error('Not connected to daemon');
        }

        try {
            const [status] = await this._proxy.SetReasoningEnabledAsync(enabled);
            return status;
        } catch (error) {
            console.error('henzai: Error setting reasoning:', error);
            throw new Error(`Failed to set reasoning: ${error.message}`);
        }
    }

    /**
     * Set callback for thinking chunks (reasoning mode)
     * @param {function} onThinking - Callback for thinking chunks
     */
    setThinkingCallback(onThinking) {
        // Disconnect previous signal if exists
        if (this._thinkingSignalId) {
            this._proxy.disconnectSignal(this._thinkingSignalId);
            this._thinkingSignalId = null;
        }
        
        // Connect new signal if callback provided
        if (onThinking) {
            this._thinkingSignalId = this._proxy.connectSignal('ThinkingChunk', (proxy, sender, [generationId, chunk]) => {
                console.log(`henzai: Received ThinkingChunk signal for ${generationId}`);
                // Only process chunks for current generation
                if (generationId === this._currentGenerationId) {
                    onThinking(chunk);
                } else {
                    console.log(`henzai: Ignoring thinking chunk from old generation: ${generationId} (current: ${this._currentGenerationId})`);
                }
            });
        }
    }

    /**
     * Get current model
     * @returns {Promise<string>} Current model ID
     */
    async getModel() {
        if (!this.isConnected()) {
            throw new Error('Not connected to daemon');
        }

        try {
            const [modelId] = await this._proxy.GetCurrentModelAsync();
            return modelId;
        } catch (error) {
            console.error('henzai: Error getting model:', error);
            throw new Error(`Failed to get model: ${error.message}`);
        }
    }

    /**
     * List available models
     * @returns {Promise<string>} JSON string of available models
     */
    async listModels() {
        if (!this.isConnected()) {
            throw new Error('Not connected to daemon');
        }

        try {
            const [modelsJson] = await this._proxy.ListModelsAsync();
            return modelsJson;
        } catch (error) {
            console.error('henzai: Error listing models:', error);
            throw new Error(`Failed to list models: ${error.message}`);
        }
    }

    /**
     * Set model
     * @param {string} modelId - Model ID to set
     * @returns {Promise<string>} Status message
     */
    async setModel(modelId) {
        if (!this.isConnected()) {
            throw new Error('Not connected to daemon');
        }

        try {
            const [status] = await this._proxy.SetModelAsync(modelId);
            return status;
        } catch (error) {
            console.error('henzai: Error setting model:', error);
            throw new Error(`Failed to set model: ${error.message}`);
        }
    }

    /**
     * Set callback for model changes
     * @param {function} onModelChanged - Callback(modelId) when model changes
     */
    setModelChangedCallback(onModelChanged) {
        // Disconnect previous signal if exists
        if (this._modelChangedSignalId) {
            this._proxy.disconnectSignal(this._modelChangedSignalId);
            this._modelChangedSignalId = null;
        }
        
        // Connect new signal if callback provided
        if (onModelChanged) {
            this._modelChangedSignalId = this._proxy.connectSignal('ModelChanged', (proxy, sender, [modelId]) => {
                console.log(`henzai: Received ModelChanged signal: ${modelId}`);
                onModelChanged(modelId);
            });
        }
    }

    /**
     * Set callback for reasoning mode changes
     * @param {function} onReasoningChanged - Callback(enabled) when reasoning mode changes
     */
    setReasoningChangedCallback(onReasoningChanged) {
        // Disconnect previous signal if exists
        if (this._reasoningChangedSignalId) {
            this._proxy.disconnectSignal(this._reasoningChangedSignalId);
            this._reasoningChangedSignalId = null;
        }
        
        // Connect new signal if callback provided
        if (onReasoningChanged) {
            this._reasoningChangedSignalId = this._proxy.connectSignal('ReasoningChanged', (proxy, sender, [enabled]) => {
                console.log(`henzai: Received ReasoningChanged signal: ${enabled}`);
                onReasoningChanged(enabled);
            });
        }
    }

    /**
     * Set callback for history cleared
     * @param {function} onHistoryCleared - Callback when history is cleared
     */
    setHistoryClearedCallback(onHistoryCleared) {
        // Disconnect previous signal if exists
        if (this._historyClearedSignalId) {
            this._proxy.disconnectSignal(this._historyClearedSignalId);
            this._historyClearedSignalId = null;
        }
        
        // Connect new signal if callback provided
        if (onHistoryCleared) {
            this._historyClearedSignalId = this._proxy.connectSignal('HistoryCleared', (proxy, sender) => {
                console.log('henzai: Received HistoryCleared signal');
                onHistoryCleared();
            });
        }
    }

    /**
     * Cleanup
     */
    destroy() {
        // Disconnect signals if connected
        if (this._signalId && this._proxy) {
            this._proxy.disconnectSignal(this._signalId);
            this._signalId = null;
        }
        if (this._thinkingSignalId && this._proxy) {
            this._proxy.disconnectSignal(this._thinkingSignalId);
            this._thinkingSignalId = null;
        }
        if (this._modelChangedSignalId && this._proxy) {
            this._proxy.disconnectSignal(this._modelChangedSignalId);
            this._modelChangedSignalId = null;
        }
        if (this._reasoningChangedSignalId && this._proxy) {
            this._proxy.disconnectSignal(this._reasoningChangedSignalId);
            this._reasoningChangedSignalId = null;
        }
        if (this._historyClearedSignalId && this._proxy) {
            this._proxy.disconnectSignal(this._historyClearedSignalId);
            this._historyClearedSignalId = null;
        }
        this._chunkCallback = null;
        this._thinkingCallback = null;
        this._proxy = null;
    }
}










