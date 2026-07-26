fx = {
    pushString: function(data) { // pushes the string into local IPC
        window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify(data));
    },
    recalculateInputRegions: function() { // SIRs
        window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify({fxAPICall: {RIR: true}}));
    },
    closeApplication: function() { // CLOSE
        window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify({fxAPICall: {CLOSE: true}}));
    }
};
