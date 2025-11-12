#!/usr/bin/gjs

const { Gio, GLib } = imports.gi;

const DBUS_NAME = 'org.gnome.henzai';
const DBUS_PATH = '/org/gnome/henzai';

const henzaiInterface = `
<node>
    <interface name="org.gnome.henzai">
        <method name="SendMessageStreaming">
            <arg type="s" name="message" direction="in"/>
        </method>
        <signal name="ResponseChunk">
            <arg type="s" name="chunk"/>
        </signal>
        <signal name="ThinkingChunk">
            <arg type="s" name="chunk"/>
        </signal>
        <signal name="StreamingComplete"/>
    </interface>
</node>
`;

const henzaiProxy = Gio.DBusProxy.makeProxyWrapper(henzaiInterface);

print('Connecting to henzai daemon...');

const proxy = new henzaiProxy(
    Gio.DBus.session,
    DBUS_NAME,
    DBUS_PATH,
    (proxy, error) => {
        if (error) {
            print(`ERROR connecting: ${error}`);
            return;
        }
        
        print('Connected successfully!');
        
        // Set up thinking callback
        let thinkingCallback = null;
        let thinkingSignalId = null;
        
        function setThinkingCallback(callback) {
            thinkingCallback = callback;
            
            if (!thinkingSignalId) {
                thinkingSignalId = proxy.connectSignal('ThinkingChunk', (proxy, sender, [chunk]) => {
                    print(`[SIGNAL] Received ThinkingChunk signal`);
                    if (thinkingCallback) {
                        thinkingCallback(chunk);
                    } else {
                        print('[WARN] Received thinking chunk but no callback set!');
                    }
                });
                print('Connected to ThinkingChunk signal');
            }
        }
        
        // Set up response chunk callback
        let responseCallback = null;
        let responseSignalId = null;
        
        function setResponseCallback(callback) {
            responseCallback = callback;
            
            if (!responseSignalId) {
                responseSignalId = proxy.connectSignal('ResponseChunk', (proxy, sender, [chunk]) => {
                    if (responseCallback) {
                        responseCallback(chunk);
                    }
                });
                print('Connected to ResponseChunk signal');
            }
        }
        
        // Set up complete signal
        let completeSignalId = proxy.connectSignal('StreamingComplete', () => {
            print('\n[COMPLETE] Streaming finished');
            loop.quit();
        });
        
        // Track chunks
        let thinkingChunks = 0;
        let responseChunks = 0;
        
        // Set callbacks
        setThinkingCallback((chunk) => {
            thinkingChunks++;
            if (thinkingChunks <= 5) {
                print(`[THINKING ${thinkingChunks}] ${chunk.substring(0, 30)}...`);
            }
        });
        
        setResponseCallback((chunk) => {
            responseChunks++;
            if (responseChunks <= 5) {
                print(`[RESPONSE ${responseChunks}] ${chunk.substring(0, 30)}...`);
            }
        });
        
        print('\nSending test query...');
        proxy.SendMessageStreamingAsync('Explain the Monty Hall problem step by step with your reasoning')
            .then(() => {
                print('Message sent successfully');
            })
            .catch((err) => {
                print(`ERROR sending message: ${err}`);
                loop.quit();
            });
        
        // Summary after complete
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, () => {
            print(`\nSUMMARY: ${thinkingChunks} thinking chunks, ${responseChunks} response chunks`);
            return GLib.SOURCE_REMOVE;
        });
    }
);

const loop = new GLib.MainLoop(null, false);

// Timeout after 60 seconds
GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 60, () => {
    print('\nTIMEOUT - stopping');
    loop.quit();
    return GLib.SOURCE_REMOVE;
});

loop.run();

