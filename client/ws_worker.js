// ws_worker.js
let ws = null;

self.onmessage = function(e) {
    const msg = e.data;

    if (msg.action === 'connect') {
        ws = new WebSocket(msg.url);

        ws.onopen = () => self.postMessage({ type: '_sys_', status: 'connected' });
        ws.onclose = () => self.postMessage({ type: '_sys_', status: 'disconnected' });
        
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                self.postMessage(data); 
            } catch (err) {}
        };
    }

    if (msg.action === 'send' && ws) {
        ws.send(JSON.stringify(msg.payload));
    }
    
    if (msg.action === 'close' && ws) {
        ws.close();
    }
};