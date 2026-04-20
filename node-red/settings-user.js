

module.exports = {


    /** By default, the Node-RED UI accepts connections on all IPv4 interfaces.
     * To listen on all IPv6 addresses, set uiHost to "::",
     * The following property can be used to listen on a specific interface. For
     * example, the following would only allow connections from the local machine.
     */
    // KHr: allow plain HTTP access 
    //uiHost: "127.0.0.1",
    uiHost: "0.0.0.0",

     /** Context Storage
      * The following property can be used to enable context storage. The configuration
      * provided here will enable file-based context that flushes to disk every 30 seconds.
      * Refer to the documentation for further options: https://nodered.org/docs/api/context/
      */
    contextStorage: {
        default: {
            module: "localfilesystem",
            config: {
                dir: "/tmp",
                base: "node-red-context",
                flushInterval: 10
            }
        }
    }

}
