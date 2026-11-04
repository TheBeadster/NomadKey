package network.columba.app.rns.api

/** Main-process memory only. Never put PINs/assertions into Intent extras or saved state. */
object NomadKeyCeremony {
    class Input(val request: String, val pin: String, val generation: Long)
    private var generation = 0L
    private var input: Input? = null
    private var response: String? = null
    private var stagedResponse: String? = null
    @Synchronized fun prepare(request: String, pin: String) {
        clear(); input = Input(request, pin, generation)
    }
    @Synchronized fun takeInput(): Input? = input.also { input = null }
    /** A key read is not yet a result: keep it private until the NFC handoff ends. */
    @Synchronized fun stageResponse(id: Long, assertion: String): Boolean {
        if(id != generation || stagedResponse != null || response != null) return false
        stagedResponse = assertion; return true
    }
    @Synchronized fun tagRemoved(id: Long): Boolean {
        if(id != generation) return false
        val staged = stagedResponse ?: return false
        stagedResponse = null; response = staged; return true
    }
    @Synchronized fun takeResponse(): String? = response.also { response = null }
    @Synchronized fun clear() { generation++; input = null; stagedResponse = null; response = null }
}
