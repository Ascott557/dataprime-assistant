// Session Replay Diagnostic Script
// Paste this into your browser console after the page loads

console.log('=== Session Replay Diagnostic ===');

// Check if RUM SDK is loaded
if (typeof window.CoralogixRum === 'undefined') {
    console.error('❌ RUM SDK not loaded!');
} else {
    console.log('✅ RUM SDK loaded');
    
    // Check session ID
    try {
        const sessionId = window.CoralogixRum.getSessionId();
        console.log('✅ Session ID:', sessionId);
    } catch (e) {
        console.error('❌ Cannot get session ID:', e.message);
    }
    
    // Check if session recording is active
    try {
        const isRecording = window.CoralogixRum._sessionRecording;
        console.log('Session Recording Object:', isRecording);
    } catch (e) {
        console.warn('⚠️ Cannot check recording status');
    }
    
    // Check for recorder instance
    if (window.CoralogixRum.recorder) {
        console.log('✅ Recorder instance exists');
    } else {
        console.warn('⚠️ No recorder instance found');
    }
    
    // Try to manually trigger recording
    try {
        window.CoralogixRum.startSessionRecording();
        console.log('✅ Manually started session recording');
    } catch (e) {
        console.warn('⚠️ Could not start recording:', e.message);
    }
}

// Check network requests to Coralogix
console.log('\n📡 Check Network tab for requests to:');
console.log('   - ingress.eu2.rum-ingress-coralogix.com');
console.log('\nLook for requests containing session replay data');

