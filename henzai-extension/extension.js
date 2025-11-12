// henzai GNOME Shell Extension
// Main extension entry point

import St from 'gi://St';
import Gio from 'gi://Gio';
import Clutter from 'gi://Clutter';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

import {ChatPanel} from './ui/chatPanel.js';
import {DaemonClient} from './dbus/client.js';

/**
 * henzai Extension
 * Provides an AI assistant integrated into GNOME Shell
 */
export default class henzaiExtension extends Extension {
    constructor(metadata) {
        super(metadata);
        this._indicator = null;
        this._chatPanel = null;
        this._daemonClient = null;
    }

    /**
     * Enable the extension
     */
    enable() {
        console.log('henzai: Enabling extension');

        try {
            // Initialize D-Bus client
            this._daemonClient = new DaemonClient();

            // Create top bar indicator
            this._createIndicator();

            // Create chat panel
            this._chatPanel = new ChatPanel(this._daemonClient, this.getSettings(), this.path);
            Main.layoutManager.addChrome(this._chatPanel.actor, {
                affectsStruts: false,
                trackFullscreen: false,
            });

            // Set up keyboard shortcut (Super+Space)
            this._setupKeybinding();

            console.log('henzai: Extension enabled successfully');
        } catch (error) {
            console.error('henzai: Error enabling extension:', error);
        }
    }

    /**
     * Disable the extension
     */
    disable() {
        console.log('henzai: Disabling extension');

        try {
            // Remove keyboard shortcut
            this._removeKeybinding();

            // Destroy chat panel
            if (this._chatPanel) {
                Main.layoutManager.removeChrome(this._chatPanel.actor);
                this._chatPanel.destroy();
                this._chatPanel = null;
            }
            
            // Destroy indicator
            if (this._indicator) {
                this._indicator.destroy();
                this._indicator = null;
            }

            // Cleanup D-Bus client
            if (this._daemonClient) {
                this._daemonClient.destroy();
                this._daemonClient = null;
            }

            console.log('henzai: Extension disabled successfully');
        } catch (error) {
            console.error('henzai: Error disabling extension:', error);
        }
    }

    /**
     * Create the top bar indicator
     */
    _createIndicator() {
        // Create a panel button
        this._indicator = new PanelMenu.Button(0.0, 'henzai', false);

        // Create icon - using henzai symbolic logo (no background)
        const iconPath = `${this.path}/data/henzai-symbolic.svg`;
        const iconFile = Gio.File.new_for_path(iconPath);
        const fileIcon = new Gio.FileIcon({ file: iconFile });
        
        const icon = new St.Icon({
            gicon: fileIcon,
            style_class: 'system-status-icon',
        });

        this._indicator.add_child(icon);

        // Add click handler to toggle chat panel
        this._indicator.connect('button-press-event', () => {
            this._toggleChatPanel();
            return Clutter.EVENT_STOP;
        });

        // Add to panel
        Main.panel.addToStatusArea('henzai-indicator', this._indicator);
    }

    /**
     * Set up keyboard shortcut
     */
    _setupKeybinding() {
        Main.wm.addKeybinding(
            'toggle-henzai',
            this.getSettings(),
            0, // flags
            Shell.ActionMode.NORMAL,
            () => this._toggleChatPanel()
        );
    }

    /**
     * Remove keyboard shortcut
     */
    _removeKeybinding() {
        Main.wm.removeKeybinding('toggle-henzai');
    }

    /**
     * Toggle the chat panel visibility
     */
    _toggleChatPanel() {
        if (this._chatPanel) {
            this._chatPanel.toggle();
        }
    }
}

