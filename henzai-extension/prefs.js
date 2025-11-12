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

        // Load models from daemon
        this._loadModels();

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

    // NOTE: _checkReasoningSupport() and _setReasoningEnabled() removed
    // Reasoning toggle removed from UI until Ramalama adds --reasoning-budget support
    // See: https://github.com/containers/ramalama/issues/XXX
    // Brain icon in chat UI still shows when reasoning models are active

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










