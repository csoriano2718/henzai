// Scrollable Text Input Widget for henzai
// A custom text input that implements StScrollable for use in St.ScrollView

import St from 'gi://St';
import Clutter from 'gi://Clutter';
import GObject from 'gi://GObject';
import Pango from 'gi://Pango';

/**
 * ScrollableTextInput - A multiline text input that can scroll
 * 
 * Implements StScrollable interface so it can be used in St.ScrollView
 * Handles basic keyboard input for Latin scripts
 */
export const ScrollableTextInput = GObject.registerClass({
    GTypeName: 'henzai_ScrollableTextInput',
    Implements: [St.Scrollable],
    Properties: {
        'hadjustment': GObject.ParamSpec.override('hadjustment', St.Scrollable),
        'vadjustment': GObject.ParamSpec.override('vadjustment', St.Scrollable),
    },
    Signals: {
        'activate': {},
        'text-changed': {},
    },
}, class ScrollableTextInput extends St.Widget {
    _init(params = {}) {
        super._init({
            reactive: true,
            can_focus: true,
            track_hover: false,  // Don't track hover - causes performance issues
            clip_to_allocation: true,  // Clip overflow content
            ...params,
        });
        
        this._hAdjustment = null;
        this._vAdjustment = null;
        this._vAdjustmentId = null;
        this._allocatedWidth = 0; // To store allocated width for height calculation
        
        // Scrolling state (controlled by chatPanel)
        this._scrollingEnabled = false;
        this._visibleHeight = 140;
        this._contentHeight = 0;
        
        this._buildUI();
        this._connectSignals();
    }

    // Padding values to match CSS (8px vertical, 12px horizontal)
    get _padding() {
        return {
            top: 8,
            bottom: 8,
            left: 12,
            right: 12
        };
    }

    // Override to properly report our size based on the text content
    vfunc_get_preferred_height(forWidth) {
        if (this._clutterText) {
            const padding = this._padding;
            // Subtract horizontal padding from width for text measurement
            const paddingWidth = padding.left + padding.right;
            const widthToUse = (forWidth > 0) ? (forWidth - paddingWidth) : ((this._allocatedWidth || 300) - paddingWidth);
            const [minHeight, naturalHeight] = this._clutterText.get_preferred_height(widthToUse);
            // Add vertical padding to reported height
            return [minHeight + padding.top + padding.bottom, naturalHeight + padding.top + padding.bottom];
        }
        return [0, 0];
    }

    vfunc_get_preferred_width(forHeight) {
        if (this._clutterText) {
            const padding = this._padding;
            const [minWidth, naturalWidth] = this._clutterText.get_preferred_width(forHeight);
            // Add horizontal padding to reported width
            return [minWidth + padding.left + padding.right, naturalWidth + padding.left + padding.right];
        }
        return [0, 0];
    }

    vfunc_allocate(box) {
        this.set_allocation(box);
        
        if (this._clutterText) {
            const padding = this._padding;
            // Get scroll offset
            const scrollY = this._vAdjustment ? this._vAdjustment.value : 0;
            
            // Create a padded box for the text
            const textBox = new Clutter.ActorBox();
            textBox.x1 = padding.left;
            textBox.y1 = padding.top - scrollY;
            textBox.x2 = box.get_width() - padding.right;
            textBox.y2 = box.get_height() - padding.bottom - scrollY;
            
            // Allocate the text with the padded box
            this._clutterText.allocate(textBox);
            
            // Store the allocated width so we can use it in get_preferred_height
            this._allocatedWidth = box.get_width();
        }
    }

    _buildUI() {
        // Create Clutter.Text for rendering
        this._clutterText = new Clutter.Text({
            text: '',
            editable: true,
            selectable: true,
            single_line_mode: false,
            activatable: true,  // Enable activate signal for Enter key
            line_wrap: true,
            line_wrap_mode: Pango.WrapMode.WORD_CHAR,
            ellipsize: Pango.EllipsizeMode.NONE,
            x_expand: true,
            font_name: 'Cantarell 10pt',
            reactive: true,  // Ensure it reacts to events
        });
        
        // Enable cursor with blinking
        this._clutterText.set_cursor_visible(true);
        this._clutterText.set_cursor_size(1);
        
        // Enable cursor blinking (requires Clutter 1.10+)
        try {
            if (this._clutterText.cursor_blink !== undefined) {
                this._clutterText.cursor_blink = true;
            }
        } catch (e) {
            // Cursor blink not supported, that's okay
        }

        this.add_child(this._clutterText);
    }

    _connectSignals() {
        // Handle mouse clicks for focus
        this.connect('button-press-event', this._onButtonPress.bind(this));
        this.connect('key-focus-in', this._onFocusIn.bind(this));
        
        // CRITICAL: Connect key-press-event to the Clutter.Text directly!
        // But connect it in capture phase so we see events before Clutter.Text processes them
        this._clutterText.connect('key-press-event', this._onKeyPress.bind(this));
        
        // Let Clutter.Text handle all keyboard input natively
        // Connect to its high-level signals instead
        this._clutterText.connect('activate', () => {
            // Clutter.Text activate signal (when Enter is pressed)
            this.emit('activate');
        });
        
        this._clutterText.connect('text-changed', () => {
            this._updateAdjustments();
            this.emit('text-changed');
        });
    }

    _updateAdjustments() {
        if (!this._vAdjustment)
            return;

        // Use the cached scrolling state set by setScrollingEnabled()
        if (this._scrollingEnabled) {
            // Content exceeds visible area - enable scrolling
            this._vAdjustment.lower = 0;
            this._vAdjustment.upper = this._contentHeight;
            this._vAdjustment.page_size = this._visibleHeight;
            this._vAdjustment.step_increment = 20;
            this._vAdjustment.page_increment = this._visibleHeight * 0.9;
            
            // Auto-scroll to keep cursor visible (scroll to bottom)
            this._vAdjustment.value = this._contentHeight - this._visibleHeight;
        } else {
            // Content fits - no scrolling needed
            const currentHeight = this._visibleHeight || 140;
            this._vAdjustment.lower = 0;
            this._vAdjustment.upper = currentHeight;
            this._vAdjustment.page_size = currentHeight;
            this._vAdjustment.value = 0;
        }
    }

    /**
     * Called by chatPanel to inform whether scrolling is needed
     * @param {boolean} enabled - Whether scrolling should be enabled
     * @param {number} visibleHeight - The target visible height (MAX_HEIGHT or less)
     * @param {number} contentHeight - The natural content height
     */
    setScrollingEnabled(enabled, visibleHeight, contentHeight) {
        this._scrollingEnabled = enabled;
        this._visibleHeight = visibleHeight;
        this._contentHeight = contentHeight;
        this._updateAdjustments();
    }

    _onFocusIn() {
        // Set key focus to the Clutter.Text child, not the container
        global.stage.set_key_focus(this._clutterText);
    }

    _onButtonPress(actor, event) {
        // Focus the Clutter.Text when clicked
        global.stage.set_key_focus(this._clutterText);
    
        // Let Clutter.Text handle the cursor positioning
        const [x, y] = event.get_coords();
        const [ok, localX, localY] = this._clutterText.transform_stage_point(x, y);
        if (ok) {
            const pos = this._clutterText.coords_to_position(localX, localY);
            this._clutterText.set_cursor_position(pos);
            this._clutterText.set_selection_bound(pos);
        }
        
        return Clutter.EVENT_STOP;
    }

    _onKeyPress(actor, event) {
        const keyval = event.get_key_symbol();
        const state = event.get_state();
        
        const ctrlPressed = (state & Clutter.ModifierType.CONTROL_MASK) !== 0;
        const shiftPressed = (state & Clutter.ModifierType.SHIFT_MASK) !== 0;
        
        // Handle Ctrl shortcuts
        if (ctrlPressed) {
            const text = this._clutterText.get_text();
            const cursorPos = this._clutterText.get_cursor_position();
            const selectionBound = this._clutterText.get_selection_bound();
            
            switch (keyval) {
                case Clutter.KEY_a:
                case Clutter.KEY_A:
                    // Select all
                    this._clutterText.set_cursor_position(0);
                    this._clutterText.set_selection_bound(text.length);
                    return Clutter.EVENT_STOP;
                    
                case Clutter.KEY_c:
                case Clutter.KEY_C:
                    // Copy - use get_selection() API instead of manual calculation
                    const selectedText = this._clutterText.get_selection();
                    if (selectedText && selectedText.length > 0) {
                        St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, selectedText);
                    }
                    return Clutter.EVENT_STOP;
                    
                case Clutter.KEY_v:
                case Clutter.KEY_V:
                    // Paste - handle selection deletion inside async callback
                    const selectedTextToPaste = this._clutterText.get_selection();
                    const pasteHasSelection = selectedTextToPaste && selectedTextToPaste.length > 0;
                    
                    // Get clipboard text and perform the paste operation
                    St.Clipboard.get_default().get_text(St.ClipboardType.CLIPBOARD, (clipboard, text) => {
                        if (!text || text.length === 0) return;
                        
                        try {
                            // If there was a selection, delete it first using Clutter's native API
                            // This must be done INSIDE the async callback to avoid race conditions
                            if (pasteHasSelection) {
                                this._clutterText.delete_selection();
                            }
                            
                            // Insert at current cursor position (after any deletion)
                            const insertPos = this._clutterText.get_cursor_position();
                            this._clutterText.insert_text(text, insertPos);
                            
                            // Ensure selection bound matches cursor (no selection after paste)
                            const newPos = this._clutterText.get_cursor_position();
                            this._clutterText.set_selection_bound(newPos);
                        } catch (e) {
                            logError(e, 'Error in paste handler');
                        }
                    });
                    return Clutter.EVENT_STOP;
                    
                case Clutter.KEY_x:
                case Clutter.KEY_X:
                    // Cut - use get_selection() API instead of manual calculation
                    const cutText = this._clutterText.get_selection();
                    if (cutText && cutText.length > 0) {
                        St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, cutText);
                        this._deleteSelection();
                    }
                    return Clutter.EVENT_STOP;
            }
        }

        // Handle Enter key for send vs newline
        if (keyval === Clutter.KEY_Return || keyval === Clutter.KEY_KP_Enter) {
            if (ctrlPressed) {
                // Ctrl+Enter = send (same as plain Enter)
                this.emit('activate');
                return Clutter.EVENT_STOP;
            } else if (shiftPressed) {
                // Shift+Enter = newline - insert manually
                this._insertText('\n');
                return Clutter.EVENT_STOP;
            } else {
                // Enter = activate
                this.emit('activate');
                return Clutter.EVENT_STOP;
            }
        }

        // Let Clutter.Text handle everything else natively
        // (regular characters, Backspace, Delete, arrow keys, Home, End, etc.)
        return Clutter.EVENT_PROPAGATE;
    }

    _insertText(newText) {
        let cursorPos = this._clutterText.get_cursor_position();
        let selectionBound = this._clutterText.get_selection_bound();
        
        if (cursorPos !== selectionBound) {
            // Delete selection first using Clutter.Text API
            const start = Math.min(cursorPos, selectionBound);
            const end = Math.max(cursorPos, selectionBound);
            this._clutterText.delete_text(start, end);
            // After deletion, cursor is at start position
            cursorPos = start;
        }
        
        // Use Clutter.Text's insert_text method directly
        // This properly handles cursor positioning
        this._clutterText.insert_text(newText, cursorPos);
        
        // insert_text automatically moves cursor to end of inserted text
        // Just ensure selection bound matches cursor (no selection)
        const newCursorPos = this._clutterText.get_cursor_position();
        this._clutterText.set_selection_bound(newCursorPos);
    }

    _deleteSelection() {
        const cursorPos = this._clutterText.get_cursor_position();
        const selectionBound = this._clutterText.get_selection_bound();
        
        if (cursorPos === selectionBound) return;
        
        const start = Math.min(cursorPos, selectionBound);
        const end = Math.max(cursorPos, selectionBound);
        
        // Use Clutter.Text's delete_text API
        this._clutterText.delete_text(start, end);
        // Cursor will be at start position
        // Ensure selection bound matches (no selection)
        this._clutterText.set_selection_bound(start);
    }

    _handleBackspace() {
        const cursorPos = this._clutterText.get_cursor_position();
        const selectionBound = this._clutterText.get_selection_bound();
        
        if (cursorPos !== selectionBound) {
            this._deleteSelection();
            return;
        }
        
        if (cursorPos > 0) {
            // Use Clutter.Text's delete_text API
            this._clutterText.delete_text(cursorPos - 1, cursorPos);
            // Cursor will be at cursorPos - 1
            // Ensure selection bound matches
            this._clutterText.set_selection_bound(cursorPos - 1);
        }
    }

    _handleDelete() {
        const cursorPos = this._clutterText.get_cursor_position();
        const selectionBound = this._clutterText.get_selection_bound();
        const text = this._clutterText.get_text();
        
        if (cursorPos !== selectionBound) {
            this._deleteSelection();
            return;
        }
        
        if (cursorPos < text.length) {
            // Use Clutter.Text's delete_text API
            this._clutterText.delete_text(cursorPos, cursorPos + 1);
            // Cursor stays at cursorPos
            // Ensure selection bound matches
            this._clutterText.set_selection_bound(cursorPos);
        }
    }

    _moveCursor(offset, selecting) {
        const cursorPos = this._clutterText.get_cursor_position();
        const newPos = Math.max(0, Math.min(this._clutterText.get_text().length, cursorPos + offset));
        
        this._clutterText.set_cursor_position(newPos);
        if (!selecting) {
            this._clutterText.set_selection_bound(newPos);
        }
    }

    // StScrollable implementation
    vfunc_get_adjustments() {
        return [this._hAdjustment, this._vAdjustment];
    }
    
    vfunc_set_adjustments(hAdj, vAdj) {
        if (this._hAdjustment === hAdj && this._vAdjustment === vAdj)
            return;
        
        // Disconnect old adjustment signals
        if (this._vAdjustment && this._vAdjustmentId) {
            this._vAdjustment.disconnect(this._vAdjustmentId);
            this._vAdjustmentId = null;
        }
            
        this._hAdjustment = hAdj;
        this._vAdjustment = vAdj;
        
        // Connect to adjustment value changes to scroll the content
        if (this._vAdjustment) {
            this._vAdjustmentId = this._vAdjustment.connect('notify::value', () => {
                this._scrollToValue();
            });
        }
        
        this.notify('hadjustment');
        this.notify('vadjustment');
        
        // Initialize adjustments now that we have them
        this._updateAdjustments();
    }
    
    _scrollToValue() {
        if (!this._vAdjustment || !this._clutterText)
            return;
        
        // Queue a relayout which will apply the scroll offset in vfunc_allocate
        this.queue_relayout();
    }
    
    get hadjustment() {
        return this._hAdjustment;
    }

    set hadjustment(adjustment) {
        if (this._hAdjustment === adjustment)
            return;
        this._hAdjustment = adjustment;
        this.notify('hadjustment');
    }

    get vadjustment() {
        return this._vAdjustment;
    }

    set vadjustment(adjustment) {
        if (this._vAdjustment === adjustment)
            return;
        this._vAdjustment = adjustment;
        this.notify('vadjustment');
    }

    // Public API
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
        global.stage.set_key_focus(this);
    }

    set_text(text) {
        this._clutterText.set_text(text);
    }

    get_text() {
        return this._clutterText.get_text();
    }
});

