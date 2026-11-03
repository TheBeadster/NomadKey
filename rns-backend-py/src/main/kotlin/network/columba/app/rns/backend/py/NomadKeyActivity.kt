package network.columba.app.rns.backend.py

import android.app.Activity
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.IsoDep
import android.content.Intent
import android.text.InputType
import android.view.WindowManager
import android.widget.*
import com.chaquo.python.Python
import com.chaquo.python.PyObject
import com.chaquo.python.android.AndroidPlatform
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/** Isolated development entry point. Never consumes Columba's normal identity or page cache. */
class NomadKeyActivity : Activity(), NfcAdapter.ReaderCallback {
    private val worker = Executors.newSingleThreadExecutor()
    private val ui = Handler(Looper.getMainLooper())
    private val busy = AtomicBoolean(false)
    private lateinit var status: TextView
    private lateinit var page: TextView
    private lateinit var host: EditText
    private lateinit var port: EditText
    private lateinit var destination: EditText
    private lateinit var serviceKey: EditText
    private lateinit var pin: EditText
    private var module: PyObject? = null
    private var adapter: NfcAdapter? = null
    @Volatile private var operation: String? = null
    @Volatile private var pinValue: String? = null
    private var publicBundle: String? = null
    private var expiresAt = 0L
    private var visible = false
    private var generation = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(null)
        window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(24,24,24,24) }
        val scroll = ScrollView(this).apply { addView(layout) }; setContentView(scroll)
        fun text(s: String) = TextView(this).also { it.text=s; layout.addView(it) }
        fun field(hint: String) = EditText(this).also {
            it.hint=hint; it.isSingleLine=true; it.isSaveEnabled=false
            it.importantForAutofill=android.view.View.IMPORTANT_FOR_AUTOFILL_NO
            layout.addView(it)
        }
        text("NomadKey DEV — Columba 2.3.1-beta")
        text("Verify and pin the full service destination and key through a trusted channel. NFC hardware compatibility is unverified.")
        host=field("Reticulum TCP transport host")
        port=field("TCP port").apply { inputType=InputType.TYPE_CLASS_NUMBER; setText("444") }
        destination=field("Full NomadNet destination (32 hex)")
        serviceKey=field("Service public key (128 hex)")
        pin=field("Authenticator FIDO2 PIN — never saved").apply { inputType=InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD }
        status=text("No authority. Enter the public service pin.")
        page=text("").apply { isSaveEnabled=false; setTextIsSelectable(false) }
        fun button(label: String, action: () -> Unit) { layout.addView(Button(this).apply { text=label; setOnClickListener { action() } }) }
        button("Verify pin and connect") {
            val h=host.text.toString().trim(); val p=port.text.toString().trim(); val d=destination.text.toString().trim(); val k=serviceKey.text.toString().trim()
            job {
                if (!Python.isStarted()) Python.start(AndroidPlatform(this))
                module=Python.getInstance().getModule("nomadkey.android")
                module!!.callAttr("configure",noBackupFilesDir.absolutePath,h,p,d,k)
                val result=module!!.callAttr("connect").toString()
                runOnUiThread {
                    if (visible) {
                        getSharedPreferences("nomadkey-public-pin",MODE_PRIVATE).edit().putString("host",h).putString("port",p).putString("destination",d).putString("key",k).apply()
                        status.text="${d.take(8)} · ${d.drop(8).dropLast(4)} · ${d.takeLast(4)}\n$result"
                    }
                }
            }
        }
        button("Enroll Flex / backup key (local approval required)") { arm("enroll") }
        button("Authenticate — tap NFC key") { arm("authenticate") }
        button("Read / refresh test page") {
            val started=generation
            job {
                val body=module!!.callAttr("read").toString()
                runOnUiThread { if (visible && started==generation && android.os.SystemClock.elapsedRealtime()<expiresAt) page.text=body }
            }
        }
        button("Forget me") { revoke() }
        button("Export public enrollment bundle") {
            if (publicBundle==null) status.text="Enroll first. No private key will be exported."
            else startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                type="application/json"; addCategory(Intent.CATEGORY_OPENABLE); putExtra(Intent.EXTRA_TITLE,"nomadkey-enrollment-public.json")
            },42)
        }
        getSharedPreferences("nomadkey-public-pin",MODE_PRIVATE).let {
            val preset=try { org.json.JSONObject(assets.open("nomadkey-test-pin.json").bufferedReader().use { r -> r.readText() }) } catch (_:Exception) { org.json.JSONObject() }
            host.setText(it.getString("host",preset.optString("host",""))); port.setText(it.getString("port","444"))
            destination.setText(it.getString("destination",preset.optString("destination",""))); serviceKey.setText(it.getString("key",preset.optString("public_key","")))
        }
        adapter=NfcAdapter.getDefaultAdapter(this)
        ui.post(tick)
    }

    private fun arm(action: String) {
        if (module==null || busy.get()) { status.text="Connect to the verified service first."; return }
        if (adapter==null || adapter?.isEnabled!=true) { status.text="NFC unavailable or disabled."; return }
        module!!.callAttr("prepare")
        operation=action; pinValue=pin.text.toString(); pin.text.clear()
        status.text="Hold Flex/YubiKey against the NFC reader until completion. UV is required."
    }

    override fun onTagDiscovered(tag: Tag) {
        val action=operation ?: return
        operation=null
        val enteredPin=pinValue ?: ""; pinValue=null
        val started=generation
        job {
            val iso=IsoDep.get(tag) ?: error("ISO-DEP required")
            iso.connect(); iso.timeout=10000
            val bridge=NfcBridge(iso)
            try {
                val result=module!!.callAttr("nfc",bridge,enteredPin,action).toString()
                val remaining=if(action=="authenticate") module!!.callAttr("remaining").toDouble() else 0.0
                runOnUiThread {
                    if(visible && started==generation) {
                        if(action=="enroll") { publicBundle=result; status.text="Credential created with UV. Export public bundle for trusted local administration; access is still denied." }
                        else { expiresAt=android.os.SystemClock.elapsedRealtime()+(remaining*1000).toLong(); status.text="Authenticated. Absolute expiry in ${remaining.toInt()} seconds." }
                    }
                }
            } finally { bridge.close() }
        }
    }

    class NfcBridge(private val iso: IsoDep) {
        fun transceive(data: ByteArray): ByteArray = iso.transceive(data)
        fun close() { try { iso.close() } catch (_: Exception) {} }
    }

    private fun job(block: () -> Unit) {
        if(!busy.compareAndSet(false,true)) return
        worker.execute {
            try { block() } catch (_: Exception) {
                runOnUiThread { page.text=""; expiresAt=0; status.text="Operation failed. No access granted. Check connection, service pin, enrollment and authenticator PIN. No automatic PIN retry." }
            } finally { busy.set(false) }
        }
    }

    private fun revoke() {
        generation++; operation=null; pinValue=null; pin.text.clear(); page.text=""; expiresAt=0
        status.text="Local view cleared. Remote revocation pending."
        Thread({
            val result=try { module?.callAttr("forget")?.toString() ?: "" } catch (_:Exception) { "" }
            val acknowledged=try { org.json.JSONObject(result).optBoolean("remote_revocation_acknowledged",false) } catch (_:Exception) { false }
            runOnUiThread { status.text=if(acknowledged) "Forgotten: server acknowledged revocation." else "Local state cleared; remote revocation NOT acknowledged. Absolute server expiry still applies." }
        }, "NomadKey-revoke").start()
    }

    private val tick=object:Runnable {
        override fun run() {
            if(expiresAt>0 && android.os.SystemClock.elapsedRealtime()>=expiresAt) { revoke() }
            ui.postDelayed(this,250)
        }
    }

    override fun onResume() {
        super.onResume(); visible=true
        adapter?.enableReaderMode(this,this,NfcAdapter.FLAG_READER_NFC_A or NfcAdapter.FLAG_READER_NFC_B or NfcAdapter.FLAG_READER_SKIP_NDEF_CHECK,null)
    }
    override fun onPause() { visible=false; adapter?.disableReaderMode(this); revoke(); super.onPause() }
    override fun onDestroy() { ui.removeCallbacks(tick); worker.shutdown(); super.onDestroy() }
    override fun onSaveInstanceState(outState: Bundle) { /* No PIN, session, page or form restoration. */ }
    @Deprecated("Development export")
    override fun onActivityResult(requestCode:Int,resultCode:Int,data:Intent?) {
        super.onActivityResult(requestCode,resultCode,data)
        if(requestCode==42 && resultCode==RESULT_OK) data?.data?.let { uri ->
            publicBundle?.let { bundle -> contentResolver.openOutputStream(uri)?.use { it.write(bundle.toByteArray()) } }
            publicBundle=null
        }
    }
}
