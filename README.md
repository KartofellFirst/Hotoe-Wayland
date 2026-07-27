# Hotoe-Wayland 

> *「ホ ト エ」.*  
> &nbsp; Built with GTk4 powered by GTK4_layer_Shell protocol  
> &nbsp; [Main repo](https://github.com/KartofellFirst/Hotoe)

---

<br>

Turn your HTML into native app in a minute!

## Showcase
`built-in parser` allows us to make simplified API calls from every part of your document.  
Instead of calling API directly, use:

### IPC related methods:

Publishing string into IPC:
> ```html
> <button onclick="push('button clicked')"></button>
> ```
> *IPC server:*
> ```bash
> button clicked
> ```
> 
> <details><summary>parses into (click):</summary>
> <pre><nobr>button onclick="fx.pushString('button clicked')"</nobr></pre></details>

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

### Input regions and focus

Setting up the input region:
> ```html
> <body SIR>...whatever...</body> <!-- SIR - Set as Input Region -->
> ```
> 
> now <body> does not allow clicks through it. OR you can do this by adding `hotoe-input-region-regulator-box` class

To update input region after something moves / resizes / disappers, run:
> 
> ```javascript
> SIRs() // SIRs - Set Input Regions
> ```
> or `fx.recalculateInputRegions()` in your JS

To manage focus events globally:
> ```javascript
> focus {
>     if (!focus) {
>         console.log("User has removed cursor from the input region")
>     }
> }
> ```
> 
> <details><summary>parses into (click):</summary>
> <pre><nobr>window.addEventListener('focusEvent', function(event) {
>     const focus = event.detail;
>     if (!focus) {
>         console.log("User has removed cursor from the input region")
>     }
> })</nobr></pre></details>

### Other:

Getting local variables after they have been setup: 
> ``` javascript
> const ipc_socket_address = {% LOCAL_BUS_ADDRESS %}
> const application_name = {% APP_NAME %}
> ```

Closing the app:
> ```javascript
> CLOSE()
> ```
> that's it. parses into `fx.closeApplication()`
--- 

<br><br><br>

## Learn more about EWAs and the Hotoe-Engine
- [Hotoe-MacOS](https://github.com/KartofellFirst/Hotoe-MacOS) 
- [Hotoe-Windows](https://github.com/FaultedSapiens/Hotoe-Windows) 
- [Main repo](https://github.com/KartofellFirst/Hotoe)

---

$${\color{gray}\sim With\ love\,\ from\ Hotoe\ Team}$$
