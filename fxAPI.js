fx = {
    pushString: function(data) {
        window.webkit.messageHandlers.busMessage.postMessage(JSON.stringify(data));
    }
};
