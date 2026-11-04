package network.columba.app.rns.api

/** Main-process memory only. Never put PINs/assertions into Intent extras or saved state. */
object NomadKeyCeremony {
    class Input(val request: String, val pin: String, val generation: Long)
    private var generation = 0L
    private var input: Input? = null
    private var response: String? = null
    @Synchronized fun prepare(request: String, pin: String) {
        clear(); input = Input(request, pin, generation)
    }
    @Synchronized fun takeInput(): Input? = input.also { input = null }
    @Synchronized fun complete(id: Long, assertion: String): Boolean {
        if(id != generation) return false
        response = assertion; return true
    }
    @Synchronized fun takeResponse(): String? = response.also { response = null }
    @Synchronized fun clear() { generation++; input = null; response = null }
}
