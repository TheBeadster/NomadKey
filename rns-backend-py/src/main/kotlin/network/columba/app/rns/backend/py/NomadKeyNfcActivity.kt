package network.columba.app.rns.backend.py

import android.app.Activity
import android.os.Bundle
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.IsoDep
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Button
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import network.columba.app.rns.api.NomadKeyCeremony
import java.util.concurrent.atomic.AtomicBoolean

/** Short NFC prompt, returns only a result code. All ceremony material stays in memory. */
class NomadKeyNfcActivity : Activity(), NfcAdapter.ReaderCallback {
    private var input: NomadKeyCeremony.Input? = null
    private var iso: IsoDep? = null
    private var adapter: NfcAdapter? = null
    private val busy = AtomicBoolean(false)
    @Volatile private var done = false
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(null)
        window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        input = NomadKeyCeremony.takeInput()
        if(input == null) { finish(); return }
        val layout=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL; setPadding(48,48,48,48) }
        layout.addView(TextView(this).apply { text="Authenticate with NFC key"; textSize=22f })
        layout.addView(TextView(this).apply { text="Hold your Flex or YubiKey against the NFC antenna until authentication finishes."; setPadding(0,24,0,24) })
        layout.addView(Button(this).apply { text="Cancel"; setOnClickListener { finish() } })
        setContentView(layout)
        adapter=NfcAdapter.getDefaultAdapter(this)
        if(adapter?.isEnabled!=true) { setResult(RESULT_CANCELED); finish() }
    }
    override fun onResume() {
        super.onResume()
        adapter?.enableReaderMode(this,this,NfcAdapter.FLAG_READER_NFC_A or NfcAdapter.FLAG_READER_NFC_B or NfcAdapter.FLAG_READER_SKIP_NDEF_CHECK,null)
    }
    override fun onTagDiscovered(tag: Tag) {
        if(!busy.compareAndSet(false,true)) return
        val data=input ?: return
        input=null
        try {
            val transport=IsoDep.get(tag) ?: error("ISO-DEP required")
            iso=transport; transport.connect(); transport.timeout=10000
            if(!Python.isStarted()) Python.start(AndroidPlatform(this))
            val result=Python.getInstance().getModule("nomadkey.browser")
                .callAttr("sign",NomadKeyActivity.NfcBridge(transport),data.pin,data.request).toString()
            runOnUiThread {
                if(!isFinishing && NomadKeyCeremony.complete(data.generation,result)) {
                    done=true; setResult(RESULT_OK)
                }
                finish()
            }
        } catch(_:Exception) { runOnUiThread { setResult(RESULT_CANCELED); finish() } }
        finally { try { iso?.close() } catch(_:Exception) {} }
    }
    override fun onPause() {
        adapter?.disableReaderMode(this)
        input=null
        try { iso?.close() } catch(_:Exception) {}
        if(!done) NomadKeyCeremony.clear()
        super.onPause()
        if(!done) finish()
    }
    override fun onSaveInstanceState(outState: Bundle) { }
}
