// henzai Preferences UI

import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class henzaiPreferences extends ExtensionPreferences {
    constructor(metadata) {
        super(metadata);
        this._models = [];
        this._modelListStore = null;
    }

    /**
     * Fill the preferences window
     */
    fillPreferencesWindow(window) {
        // Get settings
        this._settings = this.getSettings();
        
        // Create a preferences page
        const page = new Adw.PreferencesPage({
            title: 'General',
            icon_name: 'dialog-information-symbolic',
        });
        window.add(page);

        // Model Settings Group
        const modelGroup = new Adw.PreferencesGroup({
            title: 'Model Settings',
            description: 'Select the AI model to use',
        });
        page.add(modelGroup);

        // Model selection combo box
        this._modelRow = new Adw.ComboRow({
            title: 'Ramalama Model',
            subtitle: 'Select the AI model to use',
        });

        // Create StringList for model names
        this._modelListStore = new Gtk.StringList();
        this._modelRow.set_model(this._modelListStore);

        // Connect selection change
        this._modelRow.connect('notify::selected', (widget) => {
            if (widget.selected >= 0 && widget.selected < this._models.length) {
                const selectedModel = this._models[widget.selected];
                this.getSettings().set_string('model-name', selectedModel.id);
                console.log(`henzai: Model changed to ${selectedModel.id}`);
                
                // Also notify daemon via D-Bus
                this._setDaemonModel(selectedModel.id);
            }
        });

        modelGroup.add(this._modelRow);

        // Refresh button
        const refreshButton = new Gtk.Button({
            icon_name: 'view-refresh-symbolic',
            valign: Gtk.Align.CENTER,
            tooltip_text: 'Refresh model list',
        });

        refreshButton.connect('clicked', () => {
            refreshButton.set_sensitive(false);
            this._statusLabel.set_text('Loading models...');
            this._loadModels();
            // Re-enable after a delay
            GLib.timeout_add(GLib.PRIORITY_DEFAULT, 2000, () => {
                refreshButton.set_sensitive(true);
                return GLib.SOURCE_REMOVE;
            });
        });

        const refreshRow = new Adw.ActionRow({
            title: 'Refresh Model List',
            subtitle: 'Update available models from Ramalama',
        });
        refreshRow.add_suffix(refreshButton);
        refreshRow.set_activatable_widget(refreshButton);

        modelGroup.add(refreshRow);

        // Status label
        this._statusLabel = new Gtk.Label({
            label: 'Loading...',
            xalign: 0,
            margin_top: 6,
            margin_bottom: 6,
            margin_start: 12,
            margin_end: 12,
        });
        this._statusLabel.add_css_class('dim-label');
        this._statusLabel.add_css_class('caption');
        
        const statusRow = new Adw.PreferencesRow({});
        statusRow.set_child(this._statusLabel);
        modelGroup.add(statusRow);

        // Load models from daemon (after _statusLabel is created)
        this._loadModels();

        // NOTE: Reasoning toggle removed - not functional until Ramalama adds --reasoning-budget
        // See: https://github.com/containers/ramalama/issues/XXX
        // Reasoning models (DeepSeek-R1, QwQ-32B, etc.) always show reasoning chunks
        // this._reasoningRow and this._reasoningSwitch intentionally removed

        // UI Settings Group
        const uiGroup = new Adw.PreferencesGroup({
            title: 'Interface',
            description: 'Customize the interface',
        });
        page.add(uiGroup);

        // Panel position
        const positionRow = new Adw.ComboRow({
            title: 'Panel Position',
            subtitle: 'Where the chat panel appears',
        });

        const positionModel = new Gtk.StringList();
        positionModel.append('Right');
        positionModel.append('Left');
        positionModel.append('Center');

        positionRow.set_model(positionModel);
        positionRow.set_selected(
            this._getPositionIndex(this.getSettings().get_string('panel-position'))
        );

        positionRow.connect('notify::selected', (widget) => {
            const positions = ['right', 'left', 'center'];
            this.getSettings().set_string('panel-position', positions[widget.selected]);
        });

        uiGroup.add(positionRow);

        // History Group
        const historyGroup = new Adw.PreferencesGroup({
            title: 'History',
            description: 'Manage conversation history',
        });
        page.add(historyGroup);

        // Clear history button
        const clearButton = new Gtk.Button({
            label: 'Clear All History',
            valign: Gtk.Align.CENTER,
        });

        clearButton.connect('clicked', () => {
            this._showClearHistoryDialog(window);
        });

        const clearRow = new Adw.ActionRow({
            title: 'Clear Conversation History',
            subtitle: 'Delete all stored conversations',
        });
        clearRow.add_suffix(clearButton);
        clearRow.set_activatable_widget(clearButton);

        historyGroup.add(clearRow);

        // RAG Settings Group
        const ragGroup = new Adw.PreferencesGroup({
            title: 'Retrieval-Augmented Generation (RAG)',
            description: 'Ground AI responses in your local documents',
        });
        page.add(ragGroup);

        // Enable RAG toggle
        const ragEnabledRow = new Adw.SwitchRow({
            title: 'Enable RAG',
            subtitle: 'Use local documents to augment AI responses',
        });
        
        // Connect to settings (for persistence)
        this._settings.bind('rag-enabled', ragEnabledRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        
        // Also notify daemon when toggle changes
        ragEnabledRow.connect('notify::active', (widget) => {
            const enabled = widget.get_active();
            this._setRagEnabled(enabled, ragStatusRow);
        });
        
        ragGroup.add(ragEnabledRow);

        // RAG Mode selection
        const ragModeRow = new Adw.ComboRow({
            title: 'RAG Mode',
            subtitle: 'How to use indexed documents with AI responses',
        });
        
        const modeModel = new Gtk.StringList();
        modeModel.append('Augment (Docs + General Knowledge)');
        modeModel.append('Strict (Docs Only)');
        modeModel.append('Hybrid (Docs Preferred)');
        ragModeRow.set_model(modeModel);
        
        // Set selected mode
        const modes = ['augment', 'strict', 'hybrid'];
        const currentMode = this._settings.get_string('rag-mode') || 'augment';
        ragModeRow.set_selected(modes.indexOf(currentMode));
        
        // Update setting when mode changes
        ragModeRow.connect('notify::selected', (widget) => {
            const newMode = modes[widget.selected];
            this._settings.set_string('rag-mode', newMode);
            
            // If RAG is enabled, restart service with new mode
            if (this._settings.get_boolean('rag-enabled')) {
                this._setRagEnabled(true, ragStatusRow);
            }
        });
        
        ragGroup.add(ragModeRow);

        // Folder selection
        const ragFolderRow = new Adw.ActionRow({
            title: 'Document Folder',
            subtitle: this._settings.get_string('rag-folder-path') || 'No folder selected (md, pdf, docx, html, csv, xlsx supported)',
        });
        
        const folderButton = new Gtk.Button({
            label: 'Browse...',
            valign: Gtk.Align.CENTER,
        });
        
        folderButton.connect('clicked', () => {
            this._selectFolder(window, ragFolderRow);
        });
        
        ragFolderRow.add_suffix(folderButton);
        ragFolderRow.set_activatable_widget(folderButton);
        ragGroup.add(ragFolderRow);
        
        // Store folder row reference for updates
        this._ragFolderRow = ragFolderRow;

        // Format selection
        const ragFormatRow = new Adw.ComboRow({
            title: 'Vector Database Format',
            subtitle: 'Qdrant recommended for most use cases',
        });
        
        const formatModel = new Gtk.StringList();
        formatModel.append('qdrant');
        formatModel.append('json');
        formatModel.append('markdown');
        formatModel.append('milvus');
        ragFormatRow.set_model(formatModel);
        
        // Set selected format
        const formats = ['qdrant', 'json', 'markdown', 'milvus'];
        const currentFormat = this._settings.get_string('rag-format') || 'qdrant';
        ragFormatRow.set_selected(formats.indexOf(currentFormat));
        
        ragFormatRow.connect('notify::selected', (widget) => {
            this._settings.set_string('rag-format', formats[widget.selected]);
        });
        
        ragGroup.add(ragFormatRow);

        // OCR toggle
        const ragOcrRow = new Adw.SwitchRow({
            title: 'Enable OCR',
            subtitle: 'Extract text from images in PDFs (increases RAM usage)',
        });
        this._settings.bind('rag-enable-ocr', ragOcrRow, 'active', Gio.SettingsBindFlags.DEFAULT);
        ragGroup.add(ragOcrRow);

        // Status display
        const ragStatusRow = new Adw.ActionRow({
            title: 'Index Status',
            subtitle: 'Not indexed yet (first-time indexing downloads tools: ~4 GB)',
        });
        
        const reindexButton = new Gtk.Button({
            label: 'Index Now',
            valign: Gtk.Align.CENTER,
            css_classes: ['suggested-action'],
        });
        
        reindexButton.connect('clicked', () => {
            this._indexRAG(ragStatusRow, reindexButton);
        });
        
        ragStatusRow.add_suffix(reindexButton);
        ragStatusRow.set_activatable_widget(reindexButton);
        ragGroup.add(ragStatusRow);
        
        // Store status row reference for updates
        this._ragStatusRow = ragStatusRow;
        
        // Update status on load
        this._updateRAGStatus();

        // About Group
        const aboutGroup = new Adw.PreferencesGroup({
            title: 'About',
        });
        page.add(aboutGroup);

        const aboutRow = new Adw.ActionRow({
            title: 'henzai',
            subtitle: 'Local AI integrated into GNOME Shell',
        });
        aboutGroup.add(aboutRow);

        // Version row
        const versionRow = new Adw.ActionRow({
            title: 'Extension Version',
            subtitle: '0.1',
        });
        aboutGroup.add(versionRow);
    }

    /**
     * Get position index from string
     */
    _getPositionIndex(position) {
        const positions = ['right', 'left', 'center'];
        const index = positions.indexOf(position);
        return index >= 0 ? index : 0;
    }

    /**
     * Load models from daemon via D-Bus
     */
    _loadModels() {
        console.log('henzai Prefs: _loadModels() called');
        console.log('henzai Prefs: _modelRow:', this._modelRow);
        console.log('henzai Prefs: _modelListStore:', this._modelListStore);
        
        try {
            // Create D-Bus proxy
            const henzaiInterface = `
                <node>
                    <interface name="org.gnome.henzai">
                        <method name="ListModels">
                            <arg type="s" direction="out" name="models_json"/>
                        </method>
                        <method name="GetCurrentModel">
                            <arg type="s" direction="out" name="model_id"/>
                        </method>
                    </interface>
                </node>
            `;
            
            console.log('henzai Prefs: Creating D-Bus proxy...');
            const proxy = Gio.DBusProxy.makeProxyWrapper(henzaiInterface);
            const daemonProxy = new proxy(
                Gio.DBus.session,
                'org.gnome.henzai',
                '/org/gnome/henzai'
            );

            console.log('henzai Prefs: Calling ListModelsRemote...');
            // Get models list
            daemonProxy.ListModelsRemote((result, error) => {
                if (error) {
                    console.error('henzai Prefs: Error loading models:', error);
                    console.error('henzai Prefs: Error details:', error.message);
                    this._statusLabel.set_text(`Error: ${error.message}`);
                    this._addFallbackModel();
                    return;
                }

                try {
                    console.log('henzai Prefs: Got result:', result);
                    const modelsJson = result[0];
                    this._models = JSON.parse(modelsJson);
                    console.log('henzai Prefs: Parsed models:', this._models);
                    
                    // Clear existing list
                    this._modelListStore.splice(0, this._modelListStore.get_n_items(), []);
                    
                    // Add models to list
                    if (this._models.length === 0) {
                        console.log('henzai Prefs: No models found, using fallback');
                        this._addFallbackModel();
                        return;
                    }

                    this._models.forEach(model => {
                        const displayName = `${model.name} (${this._formatSize(model.size)})`;
                        console.log('henzai Prefs: Adding model to list:', displayName);
                        this._modelListStore.append(displayName);
                    });

                    // Select current model
                    this._selectCurrentModel();
                    
                    console.log(`henzai Prefs: Successfully loaded ${this._models.length} models`);
                    this._statusLabel.set_text(`${this._models.length} model(s) available`);
                } catch (e) {
                    console.error('henzai Prefs: Error parsing models:', e);
                    console.error('henzai Prefs: Stack:', e.stack);
                    this._addFallbackModel();
                }
            });

        } catch (error) {
            console.error('henzai Prefs: Error connecting to daemon:', error);
            console.error('henzai Prefs: Stack:', error.stack);
            this._addFallbackModel();
        }
    }

    /**
     * Add fallback model when daemon is unavailable
     */
    _addFallbackModel() {
        console.log('henzai Prefs: Adding fallback model');
        this._models = [{ id: 'llama3.2', name: 'llama3.2', size: 0 }];
        this._modelListStore.splice(0, this._modelListStore.get_n_items(), []);
        this._modelListStore.append('llama3.2 (default)');
        this._modelRow.set_selected(0);
        console.log('henzai Prefs: Fallback model added');
        this._statusLabel.set_text('Using fallback model (daemon not available)');
    }

    /**
     * Select the current model in the dropdown
     */
    _selectCurrentModel() {
        const currentModelId = this.getSettings().get_string('model-name') || 'llama3.2';
        const index = this._models.findIndex(m => m.id === currentModelId);
        if (index >= 0) {
            this._modelRow.set_selected(index);
        } else if (this._models.length > 0) {
            this._modelRow.set_selected(0);
        }
    }

    /**
     * Notify daemon of model change via D-Bus
     */
    _setDaemonModel(modelId) {
        try {
            const henzaiInterface = `
                <node>
                    <interface name="org.gnome.henzai">
                        <method name="SetModel">
                            <arg type="s" direction="in" name="model_id"/>
                            <arg type="s" direction="out" name="status"/>
                        </method>
                    </interface>
                </node>
            `;
            
            const proxy = Gio.DBusProxy.makeProxyWrapper(henzaiInterface);
            const daemonProxy = new proxy(
                Gio.DBus.session,
                'org.gnome.henzai',
                '/org/gnome/henzai'
            );

            daemonProxy.SetModelRemote(modelId, (result, error) => {
                if (error) {
                    console.error('henzai: Error setting model:', error);
                } else {
                    console.log('henzai:', result[0]);
                }
            });
        } catch (error) {
            console.error('henzai: Error notifying daemon:', error);
        }
    }
    
    /**
     * Select folder for RAG documents
     */
    _selectFolder(window, ragFolderRow) {
        const dialog = new Gtk.FileChooserDialog({
            title: 'Select Document Folder',
            transient_for: window,
            modal: true,
            action: Gtk.FileChooserAction.SELECT_FOLDER,
        });
        
        dialog.add_button('_Cancel', Gtk.ResponseType.CANCEL);
        dialog.add_button('_Select', Gtk.ResponseType.ACCEPT);
        
        dialog.connect('response', (dialog, response) => {
            if (response === Gtk.ResponseType.ACCEPT) {
                const folder = dialog.get_file();
                const path = folder.get_path();
                this._settings.set_string('rag-folder-path', path);
                ragFolderRow.set_subtitle(path);
                console.log(`henzai: RAG folder selected: ${path}`);
            }
            dialog.destroy();
        });
        
        dialog.show();
    }
    
    /**
     * Index RAG documents
     */
    _indexRAG(statusRow, button) {
        const folderPath = this._settings.get_string('rag-folder-path');
        
        if (!folderPath) {
            statusRow.set_subtitle('Please select a folder first');
            return;
        }
        
        const format = this._settings.get_string('rag-format');
        const enableOcr = this._settings.get_boolean('rag-enable-ocr');
        
        button.set_sensitive(false);
        statusRow.set_subtitle('Starting indexing...');
        
        try {
            const henzaiInterface = `
                <node>
                    <interface name="org.gnome.henzai">
                        <method name="SetRAGConfig">
                            <arg type="s" direction="in" name="folder_path"/>
                            <arg type="s" direction="in" name="format"/>
                            <arg type="b" direction="in" name="enable_ocr"/>
                            <arg type="b" direction="out" name="success"/>
                        </method>
                        <signal name="RAGIndexingStarted">
                            <arg type="s" name="message"/>
                        </signal>
                        <signal name="RAGIndexingProgress">
                            <arg type="s" name="message"/>
                            <arg type="i" name="percent"/>
                        </signal>
                        <signal name="RAGIndexingComplete">
                            <arg type="s" name="message"/>
                            <arg type="i" name="file_count"/>
                        </signal>
                        <signal name="RAGIndexingFailed">
                            <arg type="s" name="error"/>
                        </signal>
                    </interface>
                </node>
            `;
            
            const proxy = Gio.DBusProxy.makeProxyWrapper(henzaiInterface);
            const daemonProxy = new proxy(
                Gio.DBus.session,
                'org.gnome.henzai',
                '/org/gnome/henzai'
            );
            
            // Connect to signals
            daemonProxy.connectSignal('RAGIndexingStarted', (proxy, sender, [message]) => {
                statusRow.set_subtitle(`${message} (may download tools first time: ~4 GB)`);
            });
            
            daemonProxy.connectSignal('RAGIndexingProgress', (proxy, sender, [message, percent]) => {
                statusRow.set_subtitle(`${message} (${percent}%)`);
            });
            
            daemonProxy.connectSignal('RAGIndexingComplete', (proxy, sender, [message, fileCount]) => {
                // Show 100% completion explicitly (fixes "stuck at 80%" UI issue)
                statusRow.set_subtitle(`${message} (100%)`);
                this._settings.set_int('rag-file-count', fileCount);
                this._settings.set_string('rag-last-indexed', new Date().toISOString());
                button.set_sensitive(true);
                button.set_label('Reindex');
                console.log(`henzai: RAG indexing complete: ${fileCount} files`);
            });
            
            daemonProxy.connectSignal('RAGIndexingFailed', (proxy, sender, [error]) => {
                statusRow.set_subtitle(`Error: ${error}`);
                button.set_sensitive(true);
                console.error(`henzai: RAG indexing failed: ${error}`);
            });
            
            // Start indexing
            daemonProxy.SetRAGConfigRemote(folderPath, format, enableOcr, (result, error) => {
                if (error) {
                    statusRow.set_subtitle(`Error: ${error.message}`);
                    button.set_sensitive(true);
                    console.error('henzai: Error starting indexing:', error);
                } else {
                    console.log('henzai: Indexing started successfully');
                }
            });
            
        } catch (error) {
            statusRow.set_subtitle(`Error: ${error.message}`);
            button.set_sensitive(true);
            console.error('henzai: Error connecting to daemon:', error);
        }
    }
    
    /**
     * Update RAG status display
     */
    _updateRAGStatus() {
        if (!this._ragStatusRow) return;
        
        const folderPath = this._settings.get_string('rag-folder-path');
        const ragEnabled = this._settings.get_boolean('rag-enabled');
        
        if (!folderPath) {
            this._ragStatusRow.set_subtitle('No folder selected');
            return;
        }
        
        try {
            const henzaiInterface = `
                <node>
                    <interface name="org.gnome.henzai">
                        <method name="GetRAGStatus">
                            <arg type="s" direction="in" name="source_path"/>
                            <arg type="b" direction="in" name="rag_enabled"/>
                            <arg type="s" direction="out" name="status_json"/>
                        </method>
                    </interface>
                </node>
            `;
            
            const proxy = Gio.DBusProxy.makeProxyWrapper(henzaiInterface);
            const daemonProxy = new proxy(
                Gio.DBus.session,
                'org.gnome.henzai',
                '/org/gnome/henzai'
            );
            
            daemonProxy.GetRAGStatusRemote(folderPath, ragEnabled, (result, error) => {
                if (error) {
                    this._ragStatusRow.set_subtitle('Error getting status');
                    console.error('henzai: Error getting RAG status:', error);
                    return;
                }
                
                try {
                    const status = JSON.parse(result[0]);
                    
                    if (status.indexed && status.file_count > 0) {
                        const lastIndexed = status.last_indexed ? 
                            new Date(status.last_indexed).toLocaleString() : 
                            'unknown';
                        this._ragStatusRow.set_subtitle(
                            `Indexed ${status.file_count} files (${lastIndexed})`
                        );
                    } else {
                        this._ragStatusRow.set_subtitle('Not indexed yet (first-time indexing downloads tools: ~4 GB)');
                    }
                } catch (e) {
                    console.error('henzai: Error parsing RAG status:', e);
                    this._ragStatusRow.set_subtitle('Error parsing status');
                }
            });
            
        } catch (error) {
            console.error('henzai: Error connecting to daemon:', error);
            this._ragStatusRow.set_subtitle('Daemon not available');
        }
    }

    // NOTE: _checkReasoningSupport() and _setReasoningEnabled() removed
    // Reasoning toggle removed from UI until Ramalama adds --reasoning-budget support
    // See: https://github.com/containers/ramalama/issues/XXX
    // Brain icon in chat UI still shows when reasoning models are active
    
    /**
     * Enable or disable RAG via D-Bus
     */
    _setRagEnabled(enabled, statusRow) {
        try {
            const henzaiInterface = `
                <node>
                    <interface name="org.gnome.henzai">
                        <method name="SetRagEnabled">
                            <arg type="b" direction="in" name="enabled"/>
                            <arg type="s" direction="in" name="mode"/>
                            <arg type="s" direction="out" name="result_json"/>
                        </method>
                    </interface>
                </node>
            `;
            
            const proxy = Gio.DBusProxy.makeProxyWrapper(henzaiInterface);
            const daemonProxy = new proxy(
                Gio.DBus.session,
                'org.gnome.henzai',
                '/org/gnome/henzai'
            );
            
            // Get current RAG mode from settings
            const ragMode = this._settings.get_string('rag-mode') || 'augment';
            
            daemonProxy.SetRagEnabledRemote(enabled, ragMode, (result, error) => {
                if (error) {
                    console.error('henzai: Error setting RAG enabled:', error);
                    if (statusRow) {
                        statusRow.set_subtitle(`Error: ${error.message}`);
                    }
                    return;
                }
                
                try {
                    const response = JSON.parse(result[0]);
                    console.log('henzai: SetRagEnabled response:', response);
                    
                    if (response.success) {
                        console.log(`henzai: RAG ${enabled ? 'enabled' : 'disabled'} successfully`);
                        if (statusRow) {
                            statusRow.set_subtitle(response.message || 
                                `RAG ${enabled ? 'enabled' : 'disabled'}`);
                        }
                    } else {
                        console.error('henzai: SetRagEnabled failed:', response.error);
                        if (statusRow) {
                            statusRow.set_subtitle(`Error: ${response.error}`);
                        }
                    }
                } catch (e) {
                    console.error('henzai: Error parsing SetRagEnabled response:', e);
                }
            });
            
        } catch (error) {
            console.error('henzai: Error calling SetRagEnabled:', error);
            if (statusRow) {
                statusRow.set_subtitle(`Error: ${error.message}`);
            }
        }
    }

    /**
     * Show clear history confirmation dialog
     */
    _showClearHistoryDialog(window) {
        const dialog = new Adw.MessageDialog({
            transient_for: window,
            modal: true,
            heading: 'Clear All History?',
            body: 'This will delete all stored conversations. This action cannot be undone.',
        });

        dialog.add_response('cancel', 'Cancel');
        dialog.add_response('clear', 'Clear');
        dialog.set_response_appearance('clear', Adw.ResponseAppearance.DESTRUCTIVE);

        dialog.connect('response', (_, response) => {
            if (response === 'clear') {
                this._clearHistory();
            }
        });

        dialog.show();
    }

    /**
     * Clear conversation history via D-Bus
     */
    _clearHistory() {
        try {
            const henzaiInterface = `
                <node>
                    <interface name="org.gnome.henzai">
                        <method name="ClearHistory"/>
                    </interface>
                </node>
            `;
            
            const proxy = Gio.DBusProxy.makeProxyWrapper(henzaiInterface);
            const daemonProxy = new proxy(
                Gio.DBus.session,
                'org.gnome.henzai',
                '/org/gnome/henzai'
            );

            daemonProxy.ClearHistoryRemote((result, error) => {
                if (error) {
                    console.error('henzai: Error clearing history:', error);
                } else {
                    console.log('henzai: History cleared successfully');
                }
            });
        } catch (error) {
            console.error('henzai: Error clearing history:', error);
        }
    }

    /**
     * Format size in bytes to human-readable
     */
    _formatSize(bytes) {
        if (bytes === 0) return 'unknown';
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
    }

    /**
     * Show clear history confirmation dialog
     */
    _showClearHistoryDialog(parent) {
        const dialog = new Gtk.MessageDialog({
            transient_for: parent,
            modal: true,
            buttons: Gtk.ButtonsType.YES_NO,
            message_type: Gtk.MessageType.WARNING,
            text: 'Clear All History?',
            secondary_text: 'This will permanently delete all conversation history. This action cannot be undone.',
        });

        dialog.connect('response', (widget, response) => {
            if (response === Gtk.ResponseType.YES) {
                // Signal daemon to clear history via D-Bus
                // This would need to be implemented
                console.log('henzai: History clear requested');
            }
            dialog.destroy();
        });

        dialog.show();
    }
}










