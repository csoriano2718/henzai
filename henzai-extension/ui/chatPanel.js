// Chat panel UI for henzai

import St from 'gi://St';
import Gio from 'gi://Gio';
import Clutter from 'gi://Clutter';
import GObject from 'gi://GObject';
import GLib from 'gi://GLib';
import Pango from 'gi://Pango';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import { ScrollableTextInput } from './scrollableTextInput.js';

/**
 * Chat panel for henzai
 * Displays conversation history and input field
 */
export class ChatPanel {
    constructor(daemonClient, settings, extensionPath) {
        this._daemonClient = daemonClient;
        this._settings = settings;
        this._extensionPath = extensionPath;
        this._visible = false;
        this._messages = [];
        this._maxMessages = 100; // Limit for memory management

        this._buildUI();
    }

    /**
     * Build the chat panel UI
     */
    _buildUI() {
        // Main container - wide centered slider from top
        this.actor = new St.BoxLayout({
            style_class: 'henzai-panel',
            vertical: true,
            reactive: true,
            can_focus: true,
            track_hover: false,  // Don't track hover - causes performance issues
        });

        // Connect key press for Esc to dismiss
        this.actor.connect('key-press-event', (actor, event) => {
            const keyval = event.get_key_symbol();
            if (keyval === Clutter.KEY_Escape) {
                this.hide();
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });

        // Cache position and size calculations
        this._updatePanelGeometry();

        // Message container (scrollable) - no header now
        this._scrollView = new St.ScrollView({
            style_class: 'henzai-message-scroll',
            hscrollbar_policy: St.PolicyType.NEVER,
            vscrollbar_policy: St.PolicyType.AUTOMATIC,
            x_expand: true,
            y_expand: true,
        });

        this._messageContainer = new St.BoxLayout({
            style_class: 'henzai-message-container',
            vertical: true,
            x_expand: true,
        });

        this._scrollView.add_child(this._messageContainer);
        this.actor.add_child(this._scrollView);

        // Add input area (includes toolbar below it)
        const inputArea = this._createInputArea();
        this.actor.add_child(inputArea);

        // Add welcome message
        const welcomeMessage = `Local AI. Ask anything: "Explain quantum entanglement," "How does Rust ownership work?," or explore new ideas.`;
        this._addMessage('assistant', welcomeMessage, { isWelcome: true });
        
        // Set up D-Bus signal listeners
        this._setupSignalListeners();
    }
    
    /**
     * Set up D-Bus signal listeners for real-time synchronization
     */
    _setupSignalListeners() {
        // Listen for model changes from settings/daemon
        this._daemonClient.setModelChangedCallback((modelId) => {
            console.log(`henzai UI: Model changed to ${modelId}`);
            this._updateCurrentModel();
        });
        
        // Listen for reasoning mode changes from settings/daemon
        this._daemonClient.setReasoningChangedCallback((enabled) => {
            console.log(`henzai UI: Reasoning changed to ${enabled}`);
            this._updateReasoningToggle(enabled);
        });
        
        // Listen for history cleared (new chat or clear history)
        this._daemonClient.setHistoryClearedCallback(() => {
            console.log('henzai UI: History cleared');
            this._clearMessages();
        });
        
        // Listen for panel position changes from settings
        if (this._settings) {
            this._settingsChangedId = this._settings.connect('changed::panel-position', () => {
                console.log('henzai UI: Panel position changed');
                this._updatePanelGeometry();
                // Re-apply position if panel is visible
                if (this._visible) {
                    this.actor.x = this._cachedX;
                    this.actor.y = this._cachedY;
                }
            });
        }
    }
    
    /**
     * Update panel geometry (cached to avoid recalculating on every show)
     */
    _updatePanelGeometry() {
        const monitor = Main.layoutManager.primaryMonitor;
        const panelHeight = Main.panel.height;
        
        // Get panel position from settings (default: center)
        const position = this._settings ? this._settings.get_string('panel-position') : 'center';
        
        // Adaptive width: narrower on sides, comfortable in center
        let widthPercent;
        if (position === 'left' || position === 'right') {
            widthPercent = 0.30; // 30% on sides - narrower, less disruptive
        } else {
            widthPercent = 0.55; // 55% in center - comfortable reading width
        }
        
        const width = Math.floor(monitor.width * widthPercent);
        const height = Math.floor(monitor.height * 0.6); // 60% of screen height
        
        // Calculate x position based on alignment
        let x;
        if (position === 'left') {
            x = monitor.x;
        } else if (position === 'right') {
            x = monitor.x + monitor.width - width;
        } else { // center
            x = monitor.x + (monitor.width - width) / 2;
        }
        const y = monitor.y + panelHeight;
        
        this.actor.set_position(x, y);
        this.actor.set_size(width, height);
        
        // Cache these values
        this._panelHeight = height;
        this._panelWidth = width;
        
        // Start hidden BELOW the visible position - will slide down INTO view
        this.actor.translation_y = -height - panelHeight;
    }

    /**
     * Create the input area
     */
    _createInputArea() {
        const inputBox = new St.BoxLayout({
            style_class: 'henzai-input-box',
            x_expand: true,
            vertical: false,
        });

        // Container for input with buttons aligned at bottom
        const inputContainer = new St.BoxLayout({
            x_expand: true,
            vertical: false,
            style: 'spacing: 8px;',
        });

        // Create ScrollView for the input
        this._inputScrollView = new St.ScrollView({
            hscrollbar_policy: St.PolicyType.NEVER,
            vscrollbar_policy: St.PolicyType.NEVER,  // Start with no scrollbar, will enable dynamically
            overlay_scrollbars: true,  // Floating scrollbar inside the entry
            x_expand: true,
            y_expand: false,
            style_class: 'henzai-input-scroll',
            style: 'border-radius: 6px; border: 1px solid rgba(120, 113, 108, 0.2);',  // Warmer border
        });
        
        // Start with single-line height, will grow dynamically
        this._inputScrollView.set_height(36);
        
        // Use custom ScrollableTextInput widget
        this._inputEntry = new ScrollableTextInput({
            x_expand: true,
            y_expand: false,  // Don't expand vertically - report natural height
            style_class: 'henzai-input',
        });

        this._inputScrollView.add_child(this._inputEntry);

        // Add focus handlers for blue border
        this._inputEntry.connect('key-focus-in', () => {
            this._inputScrollView.style = 'border-radius: 6px; border: 1px solid #3584e4; box-shadow: inset 0 0 0 1px #3584e4;';
        });
        
        this._inputEntry.connect('key-focus-out', () => {
            this._inputScrollView.style = 'border-radius: 6px; border: 1px solid rgba(120, 113, 108, 0.2);';
        });

        // Handle activation (Enter key)
        this._inputEntry.connect('activate', () => {
            this._sendMessage();
        });
        
        // Handle text changes to dynamically resize input
        this._inputEntry.connect('text-changed', () => {
            this._adjustInputHeight();
        });

        inputContainer.add_child(this._inputScrollView);
        
        // Add model switcher label below input
        const modelSwitcher = this._createModelSwitcher();
        
        // Main vertical layout for input area
        const inputAreaBox = new St.BoxLayout({
            vertical: true,
            x_expand: true,
            style: 'spacing: 4px;',
        });
        
        inputAreaBox.add_child(inputContainer);
        inputAreaBox.add_child(modelSwitcher);
        
        inputBox.add_child(inputAreaBox);

        return inputBox;
    }

    /**
     * Create bottom toolbar with model switcher and all controls
     */
    _createModelSwitcher() {
        const toolbar = new St.BoxLayout({
            vertical: false,
            x_expand: true,
            style: 'spacing: 6px;',
        });
        
        // Model icon (will show brain when reasoning is enabled, appears AFTER model name)
        this._modelIcon = new St.Icon({
            icon_name: '',  // Empty by default
            icon_size: 11,
            style: 'opacity: 0; margin-left: 4px;',  // Hidden by default, margin for spacing
        });
        
        // Model label (clickable)
        this._modelLabel = new St.Label({
            text: 'Loading...',
            style: 'font-size: 9pt; opacity: 0.6;',
        });
        
        // Make it a button for clickability
        this._modelButton = new St.Button({
            style_class: 'henzai-toolbar-button',
            accessible_name: 'Switch Model',
            track_hover: true,
            child: this._modelLabel,
        });
        
        this._modelButton.connect('clicked', () => this._showModelMenu(this._modelButton));
        
        toolbar.add_child(this._modelButton);
        toolbar.add_child(this._modelIcon);  // Icon AFTER label
        
        // Status label (shows "Loading..." when Ramalama is not ready)
        this._statusLabel = new St.Label({
            text: '',
            style: 'font-size: 9pt; color: #999; margin-left: 8px;',
            visible: false,
            y_align: Clutter.ActorAlign.CENTER,
        });
        toolbar.add_child(this._statusLabel);
        
        // Spacer
        const spacer = new St.Widget({
            x_expand: true,
        });
        toolbar.add_child(spacer);
        
        // Settings button (leftmost of action buttons)
        // Load custom SVG icon (cached, similar to brain icon)
        if (!this._settingsIcon) {
            const settingsIconPath = `${this._extensionPath}/data/settings-symbolic.svg`;
            const settingsIconFile = Gio.File.new_for_path(settingsIconPath);
            this._settingsIcon = new Gio.FileIcon({ file: settingsIconFile });
        }
        
        const settingsButton = new St.Button({
            style_class: 'henzai-toolbar-button',
            accessible_name: 'Settings',
            track_hover: true,
            child: new St.Icon({
                gicon: this._settingsIcon,
                icon_size: 16,
            }),
        });
        settingsButton.connect('clicked', () => this._openSettings());
        toolbar.add_child(settingsButton);
        
        // New chat button
        const newChatButton = new St.Button({
            style_class: 'henzai-toolbar-button',
            accessible_name: 'New Chat',
            track_hover: true,
            child: new St.Icon({
                icon_name: 'list-add-symbolic',
                icon_size: 16,
            }),
        });
        newChatButton.connect('clicked', () => this._newConversation());
        toolbar.add_child(newChatButton);
        
        // Send button (rightmost, arrow up icon)
        this._sendButton = new St.Button({
            style_class: 'henzai-toolbar-button',
            accessible_name: 'Send Message',
            track_hover: true,
            child: new St.Icon({
                icon_name: 'go-up-symbolic',  // Arrow up icon
                icon_size: 16,
            }),
        });
        this._sendButton.connect('clicked', () => this._sendMessage());
        toolbar.add_child(this._sendButton);
        
        // Stop button (replaces send button when running)
        this._stopButton = new St.Button({
            style_class: 'henzai-toolbar-button',
            accessible_name: 'Stop Generation',
            visible: false,
            track_hover: true,
            child: new St.Icon({
                icon_name: 'media-playback-stop-symbolic',
                icon_size: 16,
            }),
        });
        this._stopButton.connect('clicked', async () => {
            await this._daemonClient.stopGeneration();
            
            // Finalize thinking timer if it exists
            if (this._currentStreamingMessage && 
                this._currentStreamingMessage.reasoningTimerLabel && 
                this._currentStreamingMessage.reasoningStartTime) {
                const elapsed = ((Date.now() - this._currentStreamingMessage.reasoningStartTime) / 1000).toFixed(1);
                this._currentStreamingMessage.reasoningTimerLabel.set_text(`Thought for ${elapsed}s`);
            }
            
            // Restore UI state immediately
            this._stopButton.visible = false;
            this._sendButton.visible = true;
            
            // Mark current message as stopped (if available)
            if (this._currentStreamingMessage) {
                this._currentStreamingMessage.wasStopped = true;
            }
        });
        toolbar.add_child(this._stopButton);
        
        // Load current model name
        this._updateCurrentModel();
        
        return toolbar;
    }
    
    /**
     * Update the current model label
     */
    async _updateCurrentModel() {
        try {
            // Check if daemon is connected first
            if (!this._daemonClient.isConnected()) {
                console.log('henzai: Daemon not connected yet, will retry...');
                this._modelLabel.set_text('Connecting...');
                
                // Retry after a delay
                GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 2, () => {
                    this._updateCurrentModel();
                    return GLib.SOURCE_REMOVE;
                });
                return;
            }
            
            const model = await this._daemonClient.getModel();
            
            // Simplify model name for display (remove ollama://library/ prefix, keep variant)
            let displayName = model.replace('ollama://library/', '').replace('ollama://', '').replace('library/', '');
            
            // Extract base name and variant for display
            // e.g., "deepseek-r1:14b" stays as "deepseek-r1:14b"
            this._modelLabel.set_text(displayName);
            
            // Check if reasoning is enabled and show brain icon AFTER model name
            try {
                const reasoningEnabled = await this._daemonClient.getReasoningEnabled();
                
                if (reasoningEnabled) {
                    // Load custom SVG icon only once (cached)
                    if (!this._brainIcon) {
                        const iconPath = `${this._extensionPath}/data/brain-augmented-symbolic.svg`;
                        const iconFile = Gio.File.new_for_path(iconPath);
                        this._brainIcon = new Gio.FileIcon({ file: iconFile });
                    }
                    this._modelIcon.gicon = this._brainIcon;
                    this._modelIcon.style = 'opacity: 1.0; margin-left: 2px; color: #999;';
                } else {
                    // Hide icon when reasoning is off
                    this._modelIcon.gicon = null;
                    this._modelIcon.style = 'opacity: 0; margin-left: 4px;';
                }
            } catch (iconError) {
                console.error('henzai: Error loading icon:', iconError.message);
                // Just hide icon if it fails, don't break model name display
                this._modelIcon.gicon = null;
                this._modelIcon.style = 'opacity: 0; margin-left: 4px;';
            }
        } catch (error) {
            console.error('henzai: Error getting current model:', error.message);
            this._modelLabel.set_text('Unknown model');
            
            // Retry after a delay if daemon not ready yet
            GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 2, () => {
                this._updateCurrentModel();
                return GLib.SOURCE_REMOVE;
            });
        }
    }
    
    /**
     * Show model selection menu
     */
    async _showModelMenu(sourceButton) {
        try {
            console.log('henzai: _showModelMenu called');
            // Get available models from daemon
            const modelsJson = await this._daemonClient.listModels();
            const models = JSON.parse(modelsJson);
            console.log(`henzai: Got ${models.length} models`);
            
            if (models.length === 0) {
                this._addMessage('system', 'No models available.');
                return;
            }
            
            // Add models as message with clickable buttons instead of popup menu
            const currentModel = await this._daemonClient.getModel();
            
            let message = 'Available models:\n\n';
            models.forEach(model => {
                const displayName = model.id.replace('ollama://library/', '').replace('ollama://', '').replace('library/', '');
                const isCurrent = model.id === currentModel;
                message += `${isCurrent ? '→ ' : '  '}${displayName} (${model.size_str})${isCurrent ? ' ← current' : ''}\n`;
            });
            
            this._addMessage('system', message);
            
            // Add buttons for each model
            const buttonBox = new St.BoxLayout({
                style_class: 'henzai-model-buttons',
                vertical: false,
                x_expand: true,
                x_align: Clutter.ActorAlign.START,
                // Allow buttons to wrap naturally with CSS flex-wrap
                style: 'flex-wrap: wrap;',
            });
            
            models.forEach(model => {
                const displayName = model.id.replace('ollama://library/', '').replace('ollama://', '').replace('library/', '');
                const button = new St.Button({
                    label: displayName,
                    style_class: 'henzai-model-button',
                    track_hover: false,
                });
                
                const modelId = model.id;
                button.connect('clicked', () => {
                    console.log(`henzai: Model button clicked: ${displayName}`);
                    this._switchModel(modelId);
                });
                
                buttonBox.add_child(button);
            });
            
            // Add button box to message container
            this._messageContainer.add_child(buttonBox);
            
        } catch (error) {
            console.error('henzai: Error showing model menu:', error);
            this._addMessage('system', `Error loading models: ${error.message}`);
        }
    }
    
    /**
     * Switch to a different model
     */
    async _switchModel(modelId) {
        try {
            console.log(`henzai: _switchModel called with: ${modelId}`);
            const displayName = modelId.replace('ollama://library/', '').replace('ollama://', '').replace('library/', '');
            this._addMessage('system', `Switching to model: ${displayName}...`);
            
            // Disable send button and show loading status immediately
            if (this._sendButton) {
                this._sendButton.reactive = false;
                this._sendButton.opacity = 128;
            }
            if (this._inputEntry) {
                this._inputEntry.reactive = false;
                this._inputEntry.opacity = 179;  // 0.7 * 255
            }
            if (this._statusLabel) {
                this._statusLabel.text = `⏳ Switching to ${displayName}...`;
                this._statusLabel.set_style('font-size: 9pt; color: #d97706; margin-left: 8px;');  // Orange
                this._statusLabel.visible = true;
            }
            
            console.log(`henzai: Calling setModel on daemon...`);
            const result = await this._daemonClient.setModel(modelId);
            console.log(`henzai: setModel result: ${result}`);
            this._addMessage('system', result);
            
            // Re-enable input (button will be re-enabled by status check when ready)
            if (this._inputEntry) {
                this._inputEntry.reactive = true;
                this._inputEntry.opacity = 255;  // Fully visible
            }
            
            // Update status to show loading
            if (this._statusLabel) {
                this._statusLabel.text = `⏳ Loading ${displayName}...`;
                this._statusLabel.visible = true;
            }
            
            // Update the label
            await this._updateCurrentModel();
            
            // Restart readiness polling to monitor model loading
            this._checkReadiness();
            
        } catch (error) {
            console.error('henzai: Error switching model:', error);
            this._addMessage('error', `Failed to switch model: ${error.message}`);
            
            // Re-enable input on error
            if (this._inputEntry) {
                this._inputEntry.reactive = true;
                this._inputEntry.opacity = 255;  // Fully visible
            }
            if (this._statusLabel) {
                this._statusLabel.text = `⚠️ Error switching model`;
                this._statusLabel.set_style('font-size: 9pt; color: #dc2626; margin-left: 8px;');  // Red
            }
        }
    }

    /**
     * Dynamically adjust input height based on content
     * Grows from 32px (1 line) to 140px (~5 lines), then scrolls
     */
    _adjustInputHeight() {
        if (!this._inputEntry || !this._inputScrollView)
            return;
        
        const MIN_HEIGHT = 36;   // Single line with padding (8px top + 8px bottom + ~20px text)
        const MAX_HEIGHT = 140;  // ~5 lines before scrolling
        
        // Get the natural height of the content
        const [minHeight, naturalHeight] = this._inputEntry.get_preferred_height(-1);
        
        // Clamp between MIN and MAX
        const targetHeight = Math.max(MIN_HEIGHT, Math.min(MAX_HEIGHT, naturalHeight));
        
        // Determine if scrolling is needed based on final target height
        const needsScrolling = naturalHeight > MAX_HEIGHT;
        
        console.log(`henzai: Height adjustment - natural: ${naturalHeight}px, target: ${targetHeight}px, max: ${MAX_HEIGHT}px, scrolling: ${needsScrolling}`);
        
        // Show/hide scrollbar based on whether scrolling is needed
        this._inputScrollView.vscrollbar_policy = needsScrolling ? St.PolicyType.AUTOMATIC : St.PolicyType.NEVER;
        
        // Tell the widget whether it needs scrolling BEFORE animating
        this._inputEntry.setScrollingEnabled(needsScrolling, targetHeight, naturalHeight);
        
        // Smoothly animate the height change
        this._inputScrollView.ease({
            height: targetHeight,
            duration: 150,  // 150ms smooth transition
            mode: Clutter.AnimationMode.EASE_OUT_QUAD,
        });
    }

    /**
     * Send a message to the AI
     */
    async _sendMessage() {
        const text = this._inputEntry.get_text().trim();

        if (!text) {
            return;
        }

        // If already streaming, stop the current generation first
        if (this._currentStreamingMessage) {
            console.log('henzai: Stopping previous generation before starting new one');
            await this._daemonClient.stopGeneration();
            
            // Wait a bit for streaming to fully stop
            await new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, 500, () => {
                resolve();
                return GLib.SOURCE_REMOVE;
            }));
            
            // Finalize thinking timer if it exists
            if (this._currentStreamingMessage.reasoningTimerLabel && 
                this._currentStreamingMessage.reasoningStartTime) {
                const elapsed = ((Date.now() - this._currentStreamingMessage.reasoningStartTime) / 1000).toFixed(1);
                this._currentStreamingMessage.reasoningTimerLabel.set_text(`Thought for ${elapsed}s`);
            }
            
            // Mark as stopped
            if (this._currentStreamingMessage.contentBox) {
                const stoppedLabel = new St.Label({
                    text: '⏸️ Generation stopped',
                    style: 'color: #f39c12; font-size: 9pt; font-style: italic; margin-top: 8px;',
                });
                this._currentStreamingMessage.contentBox.add_child(stoppedLabel);
            }
            
            // Clear the reference
            this._currentStreamingMessage = null;
        }

        // Clear input
        this._inputEntry.set_text('');

        // Check connection first
        if (!this._daemonClient.isConnected()) {
            this._addMessage('error', 'Not connected to henzai daemon. Please ensure the daemon is running:\n\nsystemctl --user status henzai-daemon');
            return;
        }

        // Create assistant message with user query as header (will be filled by streaming)
        const assistantMsg = this._addMessage('assistant', '', { userQuery: text });
        
        // Find the content box
        const contentBox = assistantMsg.get_children().find(child => 
            child.style_class && child.style_class.includes('henzai-response-content')
        );
        
        if (!contentBox) {
            console.error('henzai: Could not find content box');
            return;
        }

        // Show stop button in toolbar, hide send button
        this._sendButton.visible = false;
        this._stopButton.visible = true;
        
        // Track current streaming message for stop functionality
        // Track current streaming message for stop button access
        this._currentStreamingMessage = {
            wasStopped: false,
            contentBox: contentBox,
            reasoningStartTime: null,
            reasoningTimerLabel: null,
        };
        
        // Track accumulated response and reasoning
        let fullResponse = '';
        let fullReasoning = '';
        let currentRenderedContent = null;
        let reasoningSection = null;
        let reasoningLabel = null;
        let reasoningStartTime = null;
        let reasoningTimerLabel = null;
        
        // Update copy button to get the accumulated response
        if (assistantMsg._copyButton) {
            assistantMsg._copyButton._textGetter = () => fullResponse;
        }

        try {
            // Set up thinking callback for reasoning mode (fresh for this message)
            this._daemonClient.setThinkingCallback((thinkingChunk) => {
                if (!reasoningStartTime) {
                    reasoningStartTime = Date.now();
                    if (this._currentStreamingMessage) {
                        this._currentStreamingMessage.reasoningStartTime = reasoningStartTime;
                    }
                }
                
                fullReasoning += thinkingChunk;
                
                // Create reasoning section if it doesn't exist
                if (!reasoningSection) {
                    reasoningSection = this._createReasoningSection();
                    reasoningLabel = reasoningSection._reasoningLabel;
                    reasoningTimerLabel = reasoningSection._timerLabel;
                    
                    // Store in currentStreamingMessage if it still exists
                    if (this._currentStreamingMessage) {
                        this._currentStreamingMessage.reasoningTimerLabel = reasoningTimerLabel;
                    }
                    
                    contentBox.insert_child_at_index(reasoningSection, 0);  // Add at the beginning
                }
                
                // Update reasoning text
                if (reasoningLabel) {
                    reasoningLabel.set_text(fullReasoning);
                }
                
                // Update timer
                if (reasoningTimerLabel) {
                    const elapsed = ((Date.now() - reasoningStartTime) / 1000).toFixed(1);
                    reasoningTimerLabel.set_text(`Thinking for ${elapsed}s...`);
                }
            });
            
            // Throttled rendering state
            let lastRenderTime = 0;
            let pendingRender = false;
            let renderTimeout = null;
            const RENDER_THROTTLE_MS = 150;  // Max 1 render per 150ms
            
            const doRender = () => {
                // Remove old rendered content
                if (currentRenderedContent && currentRenderedContent.get_parent()) {
                    contentBox.remove_child(currentRenderedContent);
                }
                
                // Render markdown
                currentRenderedContent = this._renderMarkdown(fullResponse);
                contentBox.add_child(currentRenderedContent);
                
                lastRenderTime = Date.now();
                pendingRender = false;
                renderTimeout = null;
            };
            
            // Send with streaming and store the generation ID
            const generationId = await this._daemonClient.sendMessageStreaming(text, (chunk) => {
                // Accumulate response
                fullResponse += chunk;
                
                // Throttled rendering: only render if enough time has passed
                const now = Date.now();
                const timeSinceLastRender = now - lastRenderTime;
                
                if (timeSinceLastRender >= RENDER_THROTTLE_MS) {
                    // Enough time has passed, render immediately
                    if (renderTimeout) {
                        GLib.source_remove(renderTimeout);
                        renderTimeout = null;
                    }
                    doRender();
                } else if (!pendingRender) {
                    // Schedule a render for later
                    pendingRender = true;
                    const delay = RENDER_THROTTLE_MS - timeSinceLastRender;
                    renderTimeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, delay, () => {
                        doRender();
                        return GLib.SOURCE_REMOVE;
                    });
                }
            });
            
            // Store generation ID for comparison in signal handlers
            if (this._currentStreamingMessage) {
                this._currentStreamingMessage.generationId = generationId;
                console.log(`henzai: Stored generation ID: ${generationId}`);
            }
            
            // Note: Don't change button visibility here!
            // The await completes immediately (method returns), but chunks arrive later via signals.
            // Button visibility is restored when StreamingComplete signal is received.
            
            // Set up one-time StreamingComplete handler
            let completeSignalId = null;
            completeSignalId = this._daemonClient._proxy.connectSignal('StreamingComplete', (proxy, sender, [generationId]) => {
                console.log(`henzai: Received StreamingComplete signal for ${generationId}`);
                
                // Only process if this is for our current generation
                if (this._currentStreamingMessage && this._currentStreamingMessage.generationId === generationId) {
                    console.log(`henzai: Processing StreamingComplete for current generation`);
                    
                    // Finalize thinking timer if present
                    if (this._currentStreamingMessage.reasoningTimerLabel && 
                        this._currentStreamingMessage.reasoningStartTime) {
                        const elapsed = ((Date.now() - this._currentStreamingMessage.reasoningStartTime) / 1000).toFixed(1);
                        console.log(`henzai: Finalizing thinking timer: ${elapsed}s`);
                        this._currentStreamingMessage.reasoningTimerLabel.set_text(`Thought for ${elapsed}s`);
                    }
                    
                    // Add cancelled indicator if generation was stopped
                    if (this._currentStreamingMessage.wasStopped) {
                        const stoppedLabel = new St.Label({
                            text: '⏸️ Cancelled',
                            style: 'color: #f39c12; font-size: 9pt; font-style: italic; margin-top: 8px;',
                        });
                        this._currentStreamingMessage.contentBox.add_child(stoppedLabel);
                    }
                    
                    // Clear current streaming message reference
                    this._currentStreamingMessage = null;
                    
                    // Restore button state
                    this._stopButton.visible = false;
                    this._sendButton.visible = true;
                } else {
                    console.log(`henzai: Ignoring StreamingComplete for old generation: ${generationId}`);
                }
                
                // Disconnect this one-time handler
                try {
                    if (completeSignalId !== null) {
                        this._daemonClient._proxy.disconnectSignal(completeSignalId);
                        completeSignalId = null;
                    }
                } catch (e) {
                    console.error('henzai: Error disconnecting StreamingComplete signal:', e);
                }
            });
            
            // Final render after streaming completes (in case last chunk was throttled)
            if (pendingRender && renderTimeout) {
                GLib.source_remove(renderTimeout);
            }
            doRender();  // Always do a final render with complete content
            
            // NOTE: Finalization of thinking timer, stopped indicator, and button state 
            // are now handled in the StreamingComplete signal handler above.
            // NOTE: Don't clear thinking callback here! It's cleared when starting a new message

        } catch (error) {
            // Clean up thinking callback on error
            this._daemonClient.setThinkingCallback(null);
            
            // Clear current streaming message reference
            this._currentStreamingMessage = null;
            
            // Clean up render timeout if pending
            if (renderTimeout) {
                GLib.source_remove(renderTimeout);
                renderTimeout = null;
            }
            
            // Restore send button, hide stop button on error
            this._stopButton.visible = false;
            this._sendButton.visible = true;

            // Remove the assistant message
            this._removeMessage(assistantMsg);

            // Show error with better context
            let errorMsg = 'An error occurred. ';
            
            if (error.message.includes('not connected') || error.message.includes('daemon')) {
                errorMsg += 'The henzai daemon is not responding. Try:\n\n• systemctl --user restart henzai-daemon\n• Check logs: journalctl --user -u henzai-daemon -n 20';
            } else if (error.message.includes('timeout')) {
                errorMsg += 'The request timed out. The AI might be processing a complex request. Please try again.';
            } else {
                errorMsg += error.message;
            }
            
            this._addMessage('error', errorMsg);
            console.error('henzai: Error sending message:', error);
        }
    }

    /**
     * Create a timestamp label
     * @returns {St.Label} - Timestamp label
     */
    _createTimestamp() {
        const now = new Date();
        const hours = now.getHours().toString().padStart(2, '0');
        const minutes = now.getMinutes().toString().padStart(2, '0');
        const timeString = `${hours}:${minutes}`;
        
        return new St.Label({
            text: timeString,
            style_class: 'henzai-timestamp',
            x_align: Clutter.ActorAlign.START,
        });
    }

    /**
     * Create an animated loading indicator
     * @returns {St.BoxLayout} - Loading indicator widget
     */
    _createLoadingIndicator() {
        const loadingBox = new St.BoxLayout({
            vertical: false,
            style_class: 'henzai-loading',
        });
        
        // Use St.Spinner for proper fast animation
        const spinner = new St.Spinner({
            width: 16,
            height: 16,
            style_class: 'henzai-loading-spinner',
        });
        spinner.play();  // Start the spinner animation
        
        const loadingText = new St.Label({
            text: 'Thinking...',
            style_class: 'henzai-loading-text',
        });
        
        loadingBox.add_child(spinner);
        loadingBox.add_child(loadingText);
        
        return loadingBox;
    }

    /**
     * Create a collapsible reasoning section
     * @returns {St.BoxLayout} - Reasoning section with toggle
     */
    _createReasoningSection() {
        const reasoningBox = new St.BoxLayout({
            style_class: 'henzai-reasoning-section',
            vertical: true,
            x_expand: true,
        });
        
        // Header with toggle
        const headerBox = new St.BoxLayout({
            style_class: 'henzai-reasoning-header',
            x_expand: true,
        });
        
        const toggleIcon = new St.Label({
            text: '▼',
            style_class: 'henzai-reasoning-toggle',
        });
        
        const timerLabel = new St.Label({
            text: 'Thinking...',
            style_class: 'henzai-reasoning-timer',
        });
        
        headerBox.add_child(toggleIcon);
        headerBox.add_child(timerLabel);
        
        // Content (reasoning text) - Use Box instead of ScrollView to avoid nesting issues
        const contentBox = new St.BoxLayout({
            style_class: 'henzai-reasoning-content',
            vertical: true,
            x_expand: true,
            visible: false,  // Start collapsed
        });
        
        const reasoningLabel = new St.Label({
            style_class: 'henzai-reasoning-text',
            x_expand: true,
            y_expand: true,  // Allow vertical expansion
        });
        reasoningLabel.clutter_text.line_wrap = true;
        reasoningLabel.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
        reasoningLabel.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;  // Don't truncate
        
        contentBox.add_child(reasoningLabel);
        
        // Toggle functionality
        let isExpanded = false;  // Start collapsed
        const toggleButton = new St.Button({
            style_class: 'henzai-reasoning-header-button',
            accessible_name: 'Toggle Reasoning Details',
            x_expand: true,
            track_hover: true,
        });
        toggleButton.set_child(headerBox);
        
        toggleButton.connect('clicked', () => {
            isExpanded = !isExpanded;
            contentBox.visible = isExpanded;
            toggleIcon.set_text(isExpanded ? '▼' : '▶');
        });
        
        // Initially set collapsed state
        toggleIcon.set_text('▶');
        
        reasoningBox.add_child(toggleButton);
        reasoningBox.add_child(contentBox);
        
        // Store references for easy access
        reasoningBox._reasoningLabel = reasoningLabel;
        reasoningBox._timerLabel = timerLabel;
        reasoningBox._toggleIcon = toggleIcon;
        reasoningBox._contentBox = contentBox;
        
        return reasoningBox;
    }

    /**
     * Normalize Unicode characters to prevent display issues
     * @param {string} text - Text to normalize
     * @returns {string} - Normalized text
     */
    _normalizeText(text) {
        return text
            // Smart quotes to regular quotes
            .replace(/[\u2018\u2019]/g, "'")  // ' ' → '
            .replace(/[\u201C\u201D]/g, '"')  // " " → "
            // Em dash and en dash to regular dash
            .replace(/[\u2013\u2014]/g, '-')  // – — → -
            // Ellipsis
            .replace(/\u2026/g, '...')  // … → ...
            // Other common smart punctuation
            .replace(/\u00A0/g, ' ');  // Non-breaking space → regular space
    }

    /**
     * Parse and render markdown-like text
     * @param {string} text - Raw text with markdown
     * @returns {St.Widget} - Rendered content
     */
    _renderMarkdown(text) {
        // Normalize Unicode characters first
        text = this._normalizeText(text);
        
        const container = new St.BoxLayout({
            vertical: true,
            x_expand: true,
        });

        // Simple markdown parsing
        const lines = text.split('\n');
        let inCodeBlock = false;
        
        for (let line of lines) {
            // Code blocks
            if (line.startsWith('```')) {
                inCodeBlock = !inCodeBlock;
                continue;
            }
            
            if (inCodeBlock) {
                const codeLine = new St.Label({
                    text: line,
                    style_class: 'henzai-code-block',
                    x_expand: true,
                });
                codeLine.clutter_text.line_wrap = true;
                codeLine.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
                container.add_child(codeLine);
                continue;
            }
            
            // Empty lines
            if (!line.trim()) {
                const spacer = new St.Widget({ height: 8 });
                container.add_child(spacer);
                continue;
            }
            
            // Headings (# ## ###)
            const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
            if (headingMatch) {
                const level = headingMatch[1].length;
                const headingText = headingMatch[2];
                const fontSize = level === 1 ? '13pt' : level === 2 ? '11.5pt' : '11pt';
                const weight = level === 1 ? 700 : 600;
                
                const heading = new St.Label({
                    text: headingText,
                    style_class: 'henzai-text-line',
                    x_expand: true,
                    style: `font-size: ${fontSize}; font-weight: ${weight}; margin-top: ${level === 1 ? 12 : 8}px; margin-bottom: 4px;`,
                });
                heading.clutter_text.line_wrap = true;
                heading.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
                heading.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
                container.add_child(heading);
                continue;
            }
            
            // Bullet points - convert * or - to • and indent
            if (line.match(/^\s*[\*\-]\s+/)) {
                line = line.replace(/^\s*[\*\-]\s+/, '  • ');
            }
            
            // Numbered lists - keep the number but add consistent spacing
            if (line.match(/^\s*\d+\.\s+/)) {
                line = line.replace(/^(\s*)(\d+\.\s+)/, '$1$2');
            }
            
            // Use Pango markup for inline styling
            // Important: Handle ** before * to avoid conflicts
            let markup = line
                .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')  // **bold**
                .replace(/\*([^\*]+?)\*/g, '<i>$1</i>')  // *italic* (but not **)
                .replace(/`(.+?)`/g, '<tt>$1</tt>');     // `code`
            
            const label = new St.Label({
                text: markup,
                style_class: 'henzai-text-line',
                x_expand: true,
            });
            label.clutter_text.use_markup = true;
            label.clutter_text.line_wrap = true;
            label.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
            label.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
            
            container.add_child(label);
        }
        
        return container;
    }

    /**
     * Add a message to the conversation
     * @param {string} role - 'user', 'assistant', or 'error'
     * @param {string} text - Message text
     * @returns {St.BoxLayout} - Message actor
     */
    _addMessage(role, text, options = {}) {
        const isWelcome = options.isWelcome || false;
        const userQuery = options.userQuery || null;  // User query for assistant messages
        
        const messageBox = new St.BoxLayout({
            style_class: isWelcome ? 'henzai-message henzai-welcome-message' : `henzai-message henzai-message-${role}`,
            vertical: true,
            x_expand: true,
            opacity: 0, // Start invisible for fade-in
        });

        // For assistant messages with a user query, add it as a header
        if (role === 'assistant' && userQuery) {
            const queryContainer = new St.BoxLayout({
                vertical: true,
                x_expand: true,
            });
            
            // Header with chevron (clickable) - single line like thinking box
            const queryHeader = new St.Button({
                style_class: 'henzai-query-header',
                x_expand: true,
                can_focus: true,
                track_hover: false,
            });
            
            const headerBox = new St.BoxLayout({
                vertical: false,
                x_expand: true,
                style: 'spacing: 6px;',
            });
            
            // Chevron for expand/collapse
            const chevron = new St.Label({
                text: '▶',
                style_class: 'henzai-query-chevron',
            });
            
            // Arrow icon for single-line queries (no expand needed)
            const arrow = new St.Label({
                text: '→',
                style_class: 'henzai-query-arrow',
                visible: false,
            });
            
            // Single line header text (truncated with ellipsis)
            // Replace newlines with spaces to avoid black squares in single-line mode
            const singleLineQuery = userQuery.replace(/\n/g, ' ');
            const headerText = new St.Label({
                text: singleLineQuery,
                style_class: 'henzai-query-header-text',
                x_expand: true,
            });
            headerText.clutter_text.single_line_mode = true;
            
            headerBox.add_child(chevron);
            headerBox.add_child(arrow);
            headerBox.add_child(headerText);
            queryHeader.set_child(headerBox);
            
            // Full query text content box (hidden by default)
            const fullTextBox = new St.BoxLayout({
                vertical: true,
                x_expand: true,
                visible: false,
                style_class: 'henzai-query-content',
            });
            
            const fullText = new St.Label({
                text: userQuery,
                style_class: 'henzai-query-text',
                x_expand: true,
            });
            fullText.clutter_text.line_wrap = true;
            fullText.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
            fullText.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
            
            fullTextBox.add_child(fullText);
            
            queryContainer.add_child(queryHeader);
            queryContainer.add_child(fullTextBox);
            messageBox.add_child(queryContainer);
            
            // Check if query is actually truncated (longer than single line)
            GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
                const isTruncated = headerText.clutter_text.get_layout().is_ellipsized();
                
                if (isTruncated) {
                    // Show chevron, hide arrow - query can be expanded
                    chevron.visible = true;
                    arrow.visible = false;
                } else {
                    // Show arrow, hide chevron - query fits in one line
                    chevron.visible = false;
                    arrow.visible = true;
                }
                
                return GLib.SOURCE_REMOVE;
            });
            
            // Toggle expand/collapse on click
            let isExpanded = false;
            queryHeader.connect('clicked', () => {
                // Only allow expand if chevron is visible (query is truncated)
                if (!chevron.visible) return;
                
                isExpanded = !isExpanded;
                fullTextBox.visible = isExpanded;
                chevron.set_text(isExpanded ? '▼' : '▶');
            });
        }

        // User input: with icon instead of colored background
        if (role === 'user') {
            const userBox = new St.BoxLayout({
                vertical: false,
                x_expand: true,
                style_class: 'henzai-user-content',
                style: 'spacing: 8px;',
            });
            
            // User icon
            const userIcon = new St.Icon({
                icon_name: 'user-info-symbolic',
                icon_size: 16,
                style_class: 'henzai-user-icon',
                y_align: Clutter.ActorAlign.START,
            });
            
            const userText = new St.Label({
                text: text,
                style_class: 'henzai-user-text',
                x_expand: true,
            });
            userText.clutter_text.line_wrap = true;
            userText.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
            userText.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
            
            userBox.add_child(userIcon);
            userBox.add_child(userText);
            messageBox.add_child(userBox);
        }
        // System messages: with icon and italic text
        else if (role === 'system') {
            const systemBox = new St.BoxLayout({
                vertical: false,
                x_expand: true,
                style_class: 'henzai-system-content',
                style: 'spacing: 8px;',
            });
            
            // System icon (info icon)
            const systemIcon = new St.Icon({
                icon_name: 'dialog-information-symbolic',
                icon_size: 16,
                style_class: 'henzai-system-icon',
                y_align: Clutter.ActorAlign.START,
            });
            
            const systemText = new St.Label({
                text: text,
                style_class: 'henzai-system-text',
                x_expand: true,
            });
            systemText.clutter_text.line_wrap = true;
            systemText.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
            systemText.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
            
            systemBox.add_child(systemIcon);
            systemBox.add_child(systemText);
            messageBox.add_child(systemBox);
        }
        // Error messages: prominent with icon
        else if (role === 'error') {
            const errorBox = new St.BoxLayout({
                vertical: false,
                x_expand: true,
                style_class: 'henzai-error-content',
            });
            
            // Error icon
            const errorIcon = new St.Icon({
                icon_name: 'dialog-error-symbolic',
                icon_size: 16,
                style_class: 'henzai-error-icon',
            });
            
            const errorText = new St.Label({
                text: text,
                style_class: 'henzai-error-text',
                x_expand: true,
            });
            errorText.clutter_text.line_wrap = true;
            errorText.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
            errorText.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
            
            errorBox.add_child(errorIcon);
            errorBox.add_child(errorText);
            messageBox.add_child(errorBox);
        }
        // AI response: full-width, clean
        else {
            const contentBox = new St.BoxLayout({
                vertical: true,
                x_expand: true,
                style_class: 'henzai-response-content',
            });
            
            // Render markdown
            const rendered = this._renderMarkdown(text);
            contentBox.add_child(rendered);
            
            messageBox.add_child(contentBox);
            
            // Copy button row after AI response (for assistant only, not welcome)
            if (role === 'assistant' && !isWelcome) {
                const copyRow = new St.BoxLayout({
                    vertical: false,
                    x_expand: true,
                    style_class: 'henzai-copy-row',
                });
                
                const spacer = new St.Widget({
                    x_expand: true,
                });
                copyRow.add_child(spacer);
                
                const copyButton = new St.Button({
                    style_class: 'henzai-copy-button-bottom',
                    accessible_name: 'Copy Response',
                    track_hover: false,
                    child: new St.Icon({
                        icon_name: 'edit-copy-symbolic',
                        icon_size: 14,
                    }),
                });
                
                // Store reference to get updated text (for streaming messages)
                copyButton._textGetter = () => text;
                
                copyButton.connect('clicked', () => {
                    // Get the current text (handles streaming updates)
                    const textToCopy = copyButton._textGetter ? copyButton._textGetter() : text;
                    const clipboard = St.Clipboard.get_default();
                    clipboard.set_text(St.ClipboardType.CLIPBOARD, textToCopy);
                    
                    copyButton.child.icon_name = 'object-select-symbolic';
                    GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1200, () => {
                        copyButton.child.icon_name = 'edit-copy-symbolic';
                        return GLib.SOURCE_REMOVE;
                    });
                });
                
                copyRow.add_child(copyButton);
                messageBox.add_child(copyRow);
                
                // Store copy button reference
                messageBox._copyButton = copyButton;
            }
        }

        this._messageContainer.add_child(messageBox);
        
        // Track messages for memory management
        this._messages.push(messageBox);
        
        if (this._messages.length > this._maxMessages) {
            const oldMessage = this._messages.shift();
            if (oldMessage.get_parent() === this._messageContainer) {
                this._messageContainer.remove_child(oldMessage);
            }
        }

        // Fade-in animation
        messageBox.ease({
            opacity: 255,
            duration: 250,
            mode: Clutter.AnimationMode.EASE_OUT_QUAD,
        });

        // Auto-scroll to bottom
        this._scrollToBottom();

        return messageBox;
    }

    /**
     * Remove a message from the conversation
     * @param {St.BoxLayout} messageActor - Message to remove
     */
    _removeMessage(messageActor) {
        if (messageActor && messageActor.get_parent() === this._messageContainer) {
            this._messageContainer.remove_child(messageActor);
        }
    }

    /**
     * Scroll message view to bottom
     */
    _scrollToBottom() {
        if (!this._scrollView) {
            return;
        }

        // First attempt - immediate idle
        GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
            this._doScroll();
            return GLib.SOURCE_REMOVE;
        });

        // Second attempt - after 50ms for complex markdown
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 50, () => {
            this._doScroll();
            return GLib.SOURCE_REMOVE;
        });

        // Third attempt - after 150ms for very complex content
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 150, () => {
            this._doScroll();
            return GLib.SOURCE_REMOVE;
        });
    }

    /**
     * Actually perform the scroll
     */
    _doScroll() {
        if (!this._scrollView) {
            return;
        }

        // Get vertical adjustment using the correct method
        const vAdjustment = this._scrollView.get_vadjustment();
        if (!vAdjustment) {
            return;
        }

        const targetValue = Math.max(0, vAdjustment.upper - vAdjustment.page_size);
        vAdjustment.value = targetValue;
    }

    /**
     * Show the chat panel
     */
    show() {
        if (this._visible) return;
        
        this.actor.show();
        this._visible = true;
        
        // Setup click-away handler
        this._setupClickAwayHandler();
        
        // Check readiness before enabling UI
        this._checkReadiness();
        
        // Slide down animation
        this.actor.ease({
            translation_y: 0,
            duration: 400,
            mode: Clutter.AnimationMode.EASE_OUT_CUBIC,
            onComplete: () => {
                if (this._inputEntry) {
                    this._inputEntry.grab_key_focus();
                }
            },
        });
    }

    /**
     * Hide the chat panel
     */
    hide() {
        if (!this._visible) return;
        
        this._visible = false;
        
        // Remove click-away handler
        this._removeClickAwayHandler();
        
        // Cancel readiness check if running
        if (this._readinessTimeout) {
            GLib.source_remove(this._readinessTimeout);
            this._readinessTimeout = null;
        }
        
        // Slide up animation
        const height = this.actor.height;
        this.actor.ease({
            translation_y: -height,
            duration: 350,
            mode: Clutter.AnimationMode.EASE_IN_CUBIC,
            onComplete: () => {
                this.actor.hide();
            },
        });
    }
    
    /**
     * Check if daemon and Ramalama are ready
     * Polls GetStatus and disables UI until both are ready
     */
    _checkReadiness() {
        // Disable send button and input initially
        if (this._sendButton) {
            this._sendButton.reactive = false;
            this._sendButton.opacity = 128;
        }
        if (this._inputEntry) {
            this._inputEntry.reactive = false;
            this._inputEntry.opacity = 179;  // 0.7 * 255
        }
        
        const checkStatus = () => {
            if (!this._daemonClient.isConnected()) {
                // Daemon not connected yet, retry
                if (this._statusLabel) {
                    this._statusLabel.text = '⏳ Connecting to daemon...';
                    this._statusLabel.visible = true;
                }
                return GLib.SOURCE_CONTINUE;  // Continue polling
            }
            
            try {
                this._daemonClient._proxy.GetStatusRemote((result, error) => {
                    if (error) {
                        console.error('henzai: Error checking status:', error);
                        if (this._statusLabel) {
                            this._statusLabel.text = '⚠️  Connection error';
                            this._statusLabel.visible = true;
                        }
                        // Don't return here - the outer timeout will continue polling
                        return;
                    }
                    
                    try {
                        const status = JSON.parse(result[0]);
                        console.log('henzai: Status:', status);
                        
                        if (status.ready) {
                            // Everything is ready!
                            if (this._sendButton) {
                                this._sendButton.reactive = true;
                                this._sendButton.opacity = 255;
                            }
                            if (this._inputEntry) {
                                this._inputEntry.reactive = true;
                                this._inputEntry.opacity = 255;  // Fully visible
                            }
                            if (this._statusLabel) {
                                this._statusLabel.visible = false;
                            }
                            
                            // Stop polling - return false to stop the timeout
                            if (this._readinessTimeout) {
                                GLib.source_remove(this._readinessTimeout);
                                this._readinessTimeout = null;
                            }
                        } else {
                            // Not ready yet - show appropriate status and keep UI disabled
                            if (this._sendButton) {
                                this._sendButton.reactive = false;
                                this._sendButton.opacity = 128;
                            }
                            if (this._inputEntry) {
                                this._inputEntry.reactive = false;
                                this._inputEntry.opacity = 179;  // 0.7 * 255
                            }
                            
                            if (status.ramalama_status === 'loading' || status.ramalama_status === 'starting') {
                                if (this._statusLabel) {
                                    // Animated spinner using Unicode characters
                                    if (!this._spinnerIndex) this._spinnerIndex = 0;
                                    const spinnerFrames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];
                                    const spinner = spinnerFrames[this._spinnerIndex % spinnerFrames.length];
                                    this._spinnerIndex++;
                                    
                                    // Show the detailed message from daemon
                                    const message = status.ramalama_message || 'Loading model...';
                                    this._statusLabel.text = `${spinner} ${message}`;
                                    this._statusLabel.set_style('font-size: 9pt; color: #999; margin-left: 8px;');  // Gray for loading
                                    this._statusLabel.visible = true;
                                }
                            } else if (status.ramalama_status === 'not_started') {
                                if (this._statusLabel) {
                                    this._spinnerIndex = 0;
                                    this._statusLabel.text = `⏸️ ${status.ramalama_message || 'Service not started'}`;
                                    this._statusLabel.set_style('font-size: 9pt; color: #d97706; margin-left: 8px;');  // Orange
                                    this._statusLabel.visible = true;
                                }
                            } else if (status.ramalama_status === 'not_installed') {
                                if (this._statusLabel) {
                                    this._spinnerIndex = 0;
                                    this._statusLabel.text = `❌ ${status.ramalama_message || 'Ramalama not installed'}`;
                                    this._statusLabel.set_style('font-size: 9pt; color: #dc2626; margin-left: 8px;');  // Red
                                    this._statusLabel.visible = true;
                                }
                            } else if (status.ramalama_status === 'error') {
                                if (this._statusLabel) {
                                    this._spinnerIndex = 0;
                                    this._statusLabel.text = `⚠️ ${status.ramalama_message || 'Error'}`;
                                    this._statusLabel.set_style('font-size: 9pt; color: #dc2626; margin-left: 8px;');  // Red for errors
                                    this._statusLabel.visible = true;
                                }
                            } else if (status.ramalama_message) {
                                if (this._statusLabel) {
                                    this._spinnerIndex = 0;  // Reset spinner when not loading
                                    this._statusLabel.text = `⚠️ ${status.ramalama_message}`;
                                    this._statusLabel.set_style('font-size: 9pt; color: #d97706; margin-left: 8px;');  // Orange for warning
                                    this._statusLabel.visible = true;
                                }
                            }
                        }
                    } catch (e) {
                        console.error('henzai: Error parsing status JSON:', e);
                    }
                });
            } catch (e) {
                console.error('henzai: Error calling GetStatus:', e);
            }
            
            return GLib.SOURCE_CONTINUE;  // Continue polling
        };
        
        // Poll every 2 seconds (less aggressive)
        checkStatus();  // Check immediately
        this._readinessTimeout = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 2, checkStatus);
    }
    
    /**
     * Setup click-away handler to dismiss panel when clicking outside
     */
    _setupClickAwayHandler() {
        if (this._capturedEventId) return;
        
        // Capture events on the stage to detect clicks outside the panel
        this._capturedEventId = global.stage.connect('captured-event', (actor, event) => {
            if (event.type() !== Clutter.EventType.BUTTON_PRESS) {
                return Clutter.EVENT_PROPAGATE;
            }
            
            // Check if click is outside the panel
            const [x, y] = event.get_coords();
            if (!this.actor.contains(global.stage.get_actor_at_pos(Clutter.PickMode.ALL, x, y))) {
                this.hide();
                return Clutter.EVENT_STOP;
            }
            
            return Clutter.EVENT_PROPAGATE;
        });
    }

    /**
     * Remove click-away handler
     */
    _removeClickAwayHandler() {
        if (this._capturedEventId) {
            global.stage.disconnect(this._capturedEventId);
            this._capturedEventId = null;
        }
    }

    /**
     * Update reasoning toggle icon visibility based on state
     */
    _updateReasoningToggle(enabled) {
        // Update the brain icon visibility (it appears after model name when reasoning is on)
        if (this._modelIcon) {
            this._modelIcon.visible = enabled;
        }
    }
    
    /**
     * Clear all messages (called when history is cleared from settings or new chat)
     */
    _clearMessages() {
        // Remove all children from message container
        this._messageContainer.remove_all_children();
        
        // Clear messages array
        this._messages = [];
        
        // Re-add welcome message
        const welcomeMessage = `Local AI. Ask anything: "Explain quantum entanglement," "How does Rust ownership work?," or explore new ideas.`;
        this._addMessage('assistant', welcomeMessage, { isWelcome: true });
    }

    /**
     * Toggle panel visibility
     */
    toggle() {
        if (this._visible) {
            this.hide();
        } else {
            this.show();
        }
    }

    /**
     * Clear all messages in the conversation
     */
    _clearConversation() {
        // Remove all children from message container
        this._messageContainer.remove_all_children();
        
        // Re-add welcome message
        const welcomeMessage = `Hello! I'm henzai, your AI assistant. I can help you with:

• Launch applications: "open firefox" or "launch terminal"
• Adjust settings: "enable dark mode" or "increase volume"
• Run commands: "show disk usage" or "list processes"
• System info: "what system am I running?"

What would you like to do?`;
        this._addMessage('assistant', welcomeMessage);
        
        // TODO: In future, also clear conversation history on daemon side
    }

    /**
     * Start a new conversation
     * Clears UI and calls daemon to reset context
     */
    async _newConversation() {
        try {
            // Clear UI first
            this._messageContainer.remove_all_children();
            
            // Add welcome message
            const welcomeMessage = `Local AI. Ask anything: "Explain quantum entanglement," "How does Rust ownership work?," or explore new ideas.`;
            this._addMessage('assistant', welcomeMessage, { isWelcome: true });
            
            // Clear daemon history
            await this._daemonClient.newConversation();
            console.log('henzai: New conversation started');
        } catch (error) {
            console.error('henzai: Error starting new conversation:', error);
            this._addMessage('system', `Error starting new conversation: ${error.message}`);
        }
    }

    /**
     * Open extension settings
     */
    _openSettings() {
        // Launch gnome-extensions-app to show henzai settings
        try {
            GLib.spawn_command_line_async('gnome-extensions prefs henzai@csoriano');
        } catch (e) {
            console.error('henzai: Failed to open settings:', e);
        }
    }

    /**
     * Cleanup
     */
    destroy() {
        // Remove click-away handler if still active
        this._removeClickAwayHandler();
        
        // Disconnect settings signal
        if (this._settingsChangedId && this._settings) {
            this._settings.disconnect(this._settingsChangedId);
            this._settingsChangedId = null;
        }
        
        if (this.actor) {
            this.actor.destroy();
            this.actor = null;
        }
    }
}

