fx = {
    pushString: function(data) {
        window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify(data));
    },
    recalculateInputRegions: function() {
        window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify({fxAPICall: {RIR: true}}));
    },
    closeApplication: function() {
        window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify({fxAPICall: {CLOSE: true}}));
    }
};
