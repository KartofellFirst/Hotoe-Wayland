fx = {
    pushString: function(data) { // pushes the string into local IPC
        window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify(data));
    },
    recalculateInputRegions: function() { // SIRs
        window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify({fxAPICall: {RIR: true}}));
    },
    closeApplication: function() { // CLOSE
        window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify({fxAPICall: {CLOSE: true}}));
    },
    requestFileContent: function(filePath) { // read(path).then(file => log(file.content))
        return this._callWithPromise("readFile", { filePath: filePath });
    },

    
    // system-reserved fields
    _promises: {},
    _callCounter: 0,
    _callWithPromise: function(action, payload = {}) {
        return new Promise((resolve, reject) => {
            const callId = "call_" + (++this._callCounter) + "_" + Date.now();
            this._promises[callId] = { resolve, reject };

            const message = {
                fxAPICall: {
                    action: action,
                    callId: callId,
                    payload: payload
                }
            };
            window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify(message));
        });
    },
    _resolvePromise: function(callId, error, result) {
        if (!this._promises[callId]) return;
        
        const { resolve, reject } = this._promises[callId];
        delete this._promises[callId];

        if (error) {
            reject(new Error(error));
        } else {
            resolve(result);
        }
    }
};
