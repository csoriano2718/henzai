#!/usr/bin/env gjs

/**
 * Test script to verify D-Bus timeout settings in GJS
 */

const { Gio, GLib } = imports.gi;

const DBUS_NAME = 'org.gnome.henzai';
const DBUS_PATH = '/org/gnome/henzai';

const henzaiInterface = `
<node>
    <interface name="org.gnome.henzai">
        <method name="SendMessageStreaming">
            <arg type="s" direction="in" name="message"/>
            <arg type="s" direction="out" name="status"/>
        </method>
        <signal name="ResponseChunk">
            <arg type="s" name="chunk"/>
        </signal>
        <signal name="ThinkingChunk">
            <arg type="s" name="chunk"/>
        </signal>
    </interface>
</node>
`;

const henzaiProxy = Gio.DBusProxy.makeProxyWrapper(henzaiInterface);

print('=' .repeat(70));
print('GJS D-BUS TIMEOUT TEST');
print('=' .repeat(70));

let proxy = new henzaiProxy(
    Gio.DBus.session,
    DBUS_NAME,
    DBUS_PATH,
    (proxy, error) => {
        if (error) {
            print(`ERROR connecting: ${error}`);
            return;
        }
        
        print(`\n✅ Connected to daemon`);
        print(`   Default timeout: ${proxy.g_default_timeout}`);
        
        // Set to infinite
        proxy.g_default_timeout = -1;
        print(`   After setting to -1: ${proxy.g_default_timeout}`);
        
        print(`\n🎯 Sending long query...`);
        print(`   Expected: 30+ seconds with reasoning\n`);
        
        let chunks = 0;
        let thinkingChunks = 0;
        
        proxy.connectSignal('ResponseChunk', (proxy, sender, [chunk]) => {
            chunks++;
            if (chunks % 100 === 0) {
                print(`   📦 Response chunks: ${chunks}`);
            }
        });
        
        proxy.connectSignal('ThinkingChunk', (proxy, sender, [chunk]) => {
            thinkingChunks++;
            if (thinkingChunks % 100 === 0) {
                print(`   🧠 Thinking chunks: ${thinkingChunks}`);
            }
        });
        
        let startTime = Date.now();
        
        try {
            // Call with explicit timeout parameter
            proxy.call(
                'SendMessageStreaming',
                new GLib.Variant('(s)', ['Explain Zeno\'s paradox in detail with mathematical analysis']),
                Gio.DBusCallFlags.NONE,
                -1,  // timeout - should be infinite
                null,  // cancellable
                (proxy, asyncResult) => {
                    try {
                        let result = proxy.call_finish(asyncResult);
                        let elapsed = (Date.now() - startTime) / 1000;
                        
                        print(`\n${'='.repeat(70)}`);
                        print(`✅ D-Bus method returned after ${elapsed.toFixed(2)}s`);
                        print(`   (Signals should continue arriving...)`);
                        
                        // Wait a bit more for signals to arrive
                        GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 45, () => {
                            let totalElapsed = (Date.now() - startTime) / 1000;
                            print(`\n${'='.repeat(70)}`);
                            print(`✅ FINAL RESULTS after ${totalElapsed.toFixed(2)}s:`);
                            print(`   Response chunks: ${chunks}`);
                            print(`   Thinking chunks: ${thinkingChunks}`);
                            
                            if (totalElapsed > 25 && chunks > 0) {
                                print(`\n🎉 SUCCESS: No timeout! Signals received for ${totalElapsed.toFixed(2)}s`);
                            } else if (chunks === 0) {
                                print(`\n⚠️  WARNING: No chunks received`);
                            }
                            
                            loop.quit();
                            return false;
                        });
                    } catch (e) {
                        let elapsed = (Date.now() - startTime) / 1000;
                        print(`\n${'='.repeat(70)}`);
                        print(`❌ ERROR after ${elapsed.toFixed(2)}s:`);
                        print(`   ${e}`);
                        print(`   Message: ${e.message}`);
                        
                        if (e.message && e.message.includes('imeout')) {
                            print(`\n🔴 TIMEOUT ERROR!`);
                            print(`   Chunks before timeout:`);
                            print(`   - Response: ${chunks}`);
                            print(`   - Thinking: ${thinkingChunks}`);
                        }
                        
                        loop.quit();
                    }
                }
            );
            
        } catch (e) {
            print(`❌ Call error: ${e}`);
            loop.quit();
        }
    }
);

let loop = new GLib.MainLoop(null, false);
loop.run();

