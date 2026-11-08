package network.columba.app.rns.api

import android.content.Context
import android.util.AtomicFile
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** Public trust records only. Read from disk each time, including across RNS processes. */
object NomadKeyPins {
    data class Site(val destination: String, val publicKey: String, val name: String) {
        fun json() = JSONObject().put("destination",destination).put("public_key",publicKey).put("name",name)
    }
    fun parse(value: JSONObject): Site {
        require(value.keys().asSequence().toSet()==setOf("destination","public_key","name")) { "Invalid saved-site record" }
        val d=value.getString("destination"); val k=value.getString("public_key"); val n=value.getString("name")
        require(d.matches(Regex("[0-9a-f]{32}")) && k.matches(Regex("[0-9a-f]{128}")) && n.toByteArray().size in 1..64 && n.none { it.code<32 }) { "Invalid saved-site identity" }
        return Site(d,k,n)
    }
    private fun file(context: Context) = AtomicFile(File(context.noBackupFilesDir,"nomadkey-trusted-sites.json"))
    @Synchronized fun all(context: Context): List<Site> {
        val file=file(context)
        if (!file.baseFile.exists() && !File(file.baseFile.path+".bak").exists()) return emptyList()
        val bytes=file.openRead().use { stream ->
            val output=java.io.ByteArrayOutputStream()
            val buffer=ByteArray(1024)
            while (true) {
                val count=stream.read(buffer)
                if (count<0) break
                require(output.size()+count<=16384) { "Saved-site trust data is too large" }
                output.write(buffer,0,count)
            }
            output.toByteArray()
        }
        require(bytes.size<=16384) { "Saved-site trust data is too large" }
        val entries=JSONArray(String(bytes,Charsets.UTF_8)); require(entries.length()<=16)
        val sites=(0 until entries.length()).map { parse(entries.getJSONObject(it)) }
        require(sites.map { it.destination }.distinct().size==sites.size) { "Duplicate saved identities" }
        return sites
    }
    @Synchronized fun find(context: Context,destination: String) = all(context).firstOrNull { it.destination==destination }
    @Synchronized fun save(context: Context,site: Site) {
        parse(site.json())
        val current=all(context)
        val old=current.firstOrNull { it.destination==site.destination }
        require(old==null || old.publicKey==site.publicKey) { "Service public key conflicts with saved identity. Nothing replaced." }
        require(current.none { it.name.equals(site.name,true) && it.destination!=site.destination }) { "Another saved site uses this name. Nothing replaced." }
        val next=current.filter { it.destination!=site.destination }+site
        require(next.size<=16) { "Saved-site limit reached" }
        val array=JSONArray();next.forEach { array.put(it.json()) }
        val file=file(context); val output=file.startWrite()
        try { output.write(array.toString().toByteArray(Charsets.UTF_8));file.finishWrite(output) }
        catch(e:Exception) { file.failWrite(output);throw e }
    }
    fun verify(context: Context,destination: String,publicKey: String) {
        val pin=find(context,destination) ?: return
        require(pin.publicKey==publicKey) { "Server identity does not match the saved NFC address" }
    }
}

/** No PINs in intents, saved state or files. A late result cannot replace a newer request. */
object NomadKeyBookmarkTransfer {
    data class Input(val action:String,val pin:String,val site:String,val generation:Long)
    private var generation=0L
    private var input:Input?=null
    private var result:String?=null
    @Synchronized fun prepare(action:String,pin:String,site:String="") {
        require(action in setOf("read","save"));clear();input=Input(action,pin,site,generation)
    }
    @Synchronized fun takeInput()=input.also { input=null }
    @Synchronized fun complete(id:Long,value:String,beforeComplete:()->Unit = {}):Boolean {
        if(id!=generation || result!=null) return false
        beforeComplete();result=value;return true
    }
    @Synchronized fun takeResult()=result.also { result=null }
    @Synchronized fun clear() { generation++;input=null;result=null }
}
