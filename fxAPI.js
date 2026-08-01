Error.prototype.toJSON = function () {
    return { name: this.name, message: this.message, stack: this.stack };
};

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
    removeFile: function(filePath) { // remove(path) + optional .catch/.then
        return this._callWithPromise("removeFile", { filePath: filePath });
    },
    writeFile: function(filePath, content, isBase64 = false) { // write(path, content, isBase64?) + optional .catch/.then
        return this._callWithPromise("writeFile", { filePath: filePath, content: content, isBase64: isBase64 });
    },
    scanDirectory: function(dirPath) { // scan()
        return this._callWithPromise("scanDirectory", { dirPath: dirPath });
    },
    openExternal: function(URI) { // openExternal()
        window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify({fxAPICall: {BROWSE: URI}}))
    },
    execute: function(cmd, {timeout = 30000, daemon=false} = {}) { // exec() + optional .then/.catch
        return this._callWithPromise("execute", { cmd: cmd, timeout: timeout, daemon: daemon });
    },
    registerHotkey: function(accelerator, eventName) { // hotkey() + optional .then/.catch
        return this._callWithPromise("registerHotkey", { accelerator: accelerator, eventName: eventName });
    },
    killDaemon: function(id) { // kill(pid/id) + optional .then/.catch
        return this._callWithPromise("killDaemon", { id: id });
    },
    getDaemons: function() { // getDaemons().then
        return this._callWithPromise("getDaemons");
    },
    saveToCache: function(data, key) { // strore(data, key) 
        window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify({fxAPICall: {STORE: {data, key}}})); // not sure if that shortening works in JS
    },
    deleteFromCache: function(key) { // toss(key)
        return this._callWithPromise("deleteFromCache", { key });
    },
    getKeyValues: function() { // rob().then(keys => )
        return this._callWithPromise("getKeyValues")
    },
    getValueFromCache: function(key) { // grab(key).then(data => )
        return this._callWithPromise("getValueFromCache", {key}) // im such a niche js dev.. knowing these shorthands. mom will be proud
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
