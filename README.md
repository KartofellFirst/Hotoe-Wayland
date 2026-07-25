# Hotoe-Wayland 

> *「ホ ト エ」.*  
> &nbsp; Built with GTk4 powered by GTK4_layer_Shell protocol  
> &nbsp; [Main repo](https://github.com/KartofellFirst/Hotoe)

---

<br>

Turn your HTML into native app in a minute!

## Showcase
`built-in parser` allows us to make simplified API calls from every part of your document.  
Instead of calling API directly ```fx.pushString()``` use:

> ```html
> <button onclick="push('button clicked')"></button>
> ```
> *IPC server:*
> ```bash
> button clicked
> ```

Adding IPC message listener:
> ```javascript
> receive {
>     console.log(message);
>     push("Got your message, dear backend!")
> }
> ```
> 
> <details><summary>parses into (click):</summary>
> <pre><nobr>window.addEventListener('busMessage', function(event) {
>     const message = event.detail;
>     console.log(message);
>     push("Got your message, dear backend!")
> })</nobr></pre></details>

Getting local variables after they have been setup: 
> ``` javascript
> const ipc_socket_address = {% LOCAL_BUS_ADDRESS %}
> const application_name = {% APP_NAME %}
> ```

--- 

<br><br><br>

## Learn more about EWAs and the Hotoe-Engine
- [Hotoe-MacOS](https://github.com/KartofellFirst/Hotoe-MacOS) 
- [Hotoe-Windows](https://github.com/FaultedSapiens/Hotoe-Windows) 
- [Main repo](https://github.com/KartofellFirst/Hotoe)

---

$${\color{gray}\sim With\ love\,\ from\ Hotoe\ Team}$$
