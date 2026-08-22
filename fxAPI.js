Error.prototype.toJSON = function () {
    return { name: this.name, message: this.message, stack: this.stack };
};

function push(data) { // pushes the string into local IPC
    window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify(data));
}
function SIRs() { // SIRs
    window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify({fxAPICall: {RIR: true}}));
}
function CLOSE() { // CLOSE
    window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify({fxAPICall: {CLOSE: true}}));
}
function read(filePath) { // read(path).then(file => log(file.content))
    return fx._callWithPromise("readFile", { filePath: filePath });
}
function remove(filePath) { // remove(path) + optional .catch/.then
    return fx._callWithPromise("removeFile", { filePath: filePath });
}
function write(filePath, content, isBase64 = false) { // write(path, content, isBase64?) + optional .catch/.then
    return fx._callWithPromise("writeFile", { filePath: filePath, content: content, isBase64: isBase64 });
}
function scan(dirPath) { // scan()
    return fx._callWithPromise("scanDirectory", { dirPath: dirPath });
}
function openExternal(URI) { // openExternal()
    window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify({fxAPICall: {BROWSE: URI}}))
}
function exec(cmd, {timeout = 30000, daemon=false} = {}) { // exec() + optional .then/.catch
    return fx._callWithPromise("execute", { cmd: cmd, timeout: timeout, daemon: daemon });
}
function hotkey(accelerator, eventName) { // hotkey() + optional .then/.catch
    return fx._callWithPromise("registerHotkey", { accelerator: accelerator, eventName: eventName });
}
function kill(id) { // kill(pid/id) + optional .then/.catch
    return fx._callWithPromise("killDaemon", { id: id });
}
function getDaemons() { // getDaemons().then
    return fx._callWithPromise("getDaemons");
}
function store(data, key) { // store(data, key) 
    window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify({fxAPICall: {STORE: {data, key}}})); // not sure if that shortening works in JS
}
function toss(key) { // toss(key)
    return fx._callWithPromise("deleteFromCache", { key });
}
function rob() { // rob().then(keys => )
    return fx._callWithPromise("getKeyValues")
}
function grab(key) { // grab(key).then(data => )
    return fx._callWithPromise("getValueFromCache", {key}) // im such a niche js dev.. knowing these shorthands. mom will be proud
}

const SIR = "hotoe-input-region-regulator-box"

fx = {
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
