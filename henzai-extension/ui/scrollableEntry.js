// Scrollable Entry Widget for henzai
// Uses Clutter.Text inside St.ScrollView for multiline scrollable input

import St from 'gi://St';
import Clutter from 'gi://Clutter';
import GObject from 'gi://GObject';
import Pango from 'gi://Pango';

/**
 * ScrollableEntry - A multiline text entry with actual scrolling
 * 
 * This combines:
 * - St.ScrollView for scrolling capability
 * - Clutter.Text for text rendering and input
 */
export const ScrollableEntry = GObject.registerClass({
    GTypeName: 'henzai_ScrollableEntry',
    Properties: {
        'text': GObject.ParamSpec.string(
            'text',
            'Text',
            'The text content',
            GObject.ParamFlags.READWRITE,
            ''
        ),
    },
    Signals: {
        'activate': {},
    },
}, class ScrollableEntry extends St.Widget {
    _init(params = {}) {
        super._init({
            layout_manager: new Clutter.BinLayout(),
            reactive: true,
            can_focus: true,
            track_hover: false,  // Don't track hover - causes performance issues
            style: 'background-color: #ffffff; border-radius: 6px; border: 1px solid rgba(0, 0, 0, 0.15);',
            ...params,
        });

        this._buildUI();
    }

    _buildUI() {
        // Create ScrollView for scrolling
        this._scrollView = new St.ScrollView({
            hscrollbar_policy: St.PolicyType.NEVER,
            vscrollbar_policy: St.PolicyType.AUTOMATIC,
            overlay_scrollbars: true,
            x_expand: true,
            style: 'padding: 6px 10px; max-height: 120px; min-height: 32px; color: #1a1a1a;',
        });

        // Create Clutter.Text for the actual text input
        this._clutterText = new Clutter.Text({
            text: '',
            editable: true,
            selectable: true,
            single_line_mode: false,
            activatable: false,
            line_wrap: true,
            line_wrap_mode: Pango.WrapMode.WORD_CHAR,
            ellipsize: Pango.EllipsizeMode.NONE,
            x_expand: true,
            font_name: 'Cantarell 10pt',
        });
        
        // Try to set color using set_color method with plain object
        try {
            const color = { red: 26, green: 26, blue: 26, alpha: 255 };
            this._clutterText.set_color(color);
        } catch (e) {
            console.log('henzai: Could not set text color:', e.message);
        }

        // Note: Shell.Entry is not available/needed in this context
        // Clutter.Text should handle input directly when it has key focus
        // this._shellEntry = new Shell.Entry(this._clutterText);

        // Add ClutterText to ScrollView
        this._scrollView.add_child(this._clutterText);
        this.add_child(this._scrollView);

        // Make the whole widget clickable to focus the text
        this.connect('button-press-event', (actor, event) => {
            this.grab_key_focus();
            return Clutter.EVENT_STOP;
        });

        // Debug logging
        this._clutterText.connect('text-changed', () => {
            console.log('henzai: Text changed to:', this._clutterText.get_text());
        });
    }

    // Override grab_key_focus to focus the Clutter.Text
    vfunc_key_focus_in() {
        global.stage.set_key_focus(this._clutterText);
    }

    // Compatibility interface for chatPanel.js
    get text() {
        return this._clutterText.get_text();
    }

    set text(value) {
        this._clutterText.set_text(value);
    }

    get clutter_text() {
        return this._clutterText;
    }

    grab_key_focus() {
        global.stage.set_key_focus(this._clutterText);
    }

    set_text(text) {
        this._clutterText.set_text(text);
    }

    get_text() {
        return this._clutterText.get_text();
    }
});
