package network.columba.app.rns.backend.py

import android.app.Activity
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.IsoDep
import android.view.View
import android.view.WindowManager
import android.widget.*
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import network.columba.app.rns.api.NomadKeyBookmarkTransfer
import network.columba.app.rns.api.NomadKeyPins
import org.json.JSONObject
import java.util.concurrent.atomic.AtomicBoolean

/** Separate from the 15-second login prompt. Writes are never automatically retried. */
class NomadKeyBookmarkActivity : Activity(), NfcAdapter.ReaderCallback {
    private val ui=Handler(Looper.getMainLooper())
    private val busy=AtomicBoolean(false)
    @Volatile private var active=true
    @Volatile private var iso:IsoDep?=null
    private var input:NomadKeyBookmarkTransfer.Input?=null
    private var generation=0L
    private var done=false
    private var deadline=0L
    private var adapter:NfcAdapter?=null
    private lateinit var status:TextView
    private lateinit var progress:ProgressBar
    private lateinit var choices:LinearLayout
    private val timeout=Runnable {
        active=false;input=null
        try { iso?.close() } catch(_:Exception) {}
        failed("NFC operation timed out. If saving, the key may contain an incomplete bookmark. Read it before trying another save.")
    }
    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(null)
        window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        input=NomadKeyBookmarkTransfer.takeInput()
        val data=input ?: run { finish();return }
        generation=data.generation;deadline=SystemClock.elapsedRealtime()+60000
        val pad=(24*resources.displayMetrics.density).toInt()
        val layout=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(pad,pad,pad,pad) }
        layout.addView(TextView(this).apply { text=if(data.action=="read") "Read NFC saved address" else "Save verified site to NFC key";textSize=22f })
        status=TextView(this).apply { text="Present your Flex or YubiKey and keep it steady. This can take up to 60 seconds. No automatic retry.";setPadding(0,pad,0,pad);accessibilityLiveRegion=View.ACCESSIBILITY_LIVE_REGION_POLITE }
        progress=ProgressBar(this).apply { visibility=View.GONE }
        choices=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL }
        layout.addView(status);layout.addView(progress);layout.addView(choices)
        layout.addView(Button(this).apply { text="Cancel";setOnClickListener { finish() } })
        setContentView(ScrollView(this).apply { addView(layout) })
        adapter=NfcAdapter.getDefaultAdapter(this)
        if(adapter?.isEnabled!=true) failed("NFC is unavailable. Enable NFC and try again.")
        else ui.postDelayed(timeout,60000)
    }
    override fun onResume() {
        super.onResume()
        if(adapter?.isEnabled==true) adapter?.enableReaderMode(this,this,
            NfcAdapter.FLAG_READER_NFC_A or NfcAdapter.FLAG_READER_NFC_B or NfcAdapter.FLAG_READER_SKIP_NDEF_CHECK,null)
    }
    override fun onTagDiscovered(tag:Tag) {
        if(!active || !busy.compareAndSet(false,true)) return
        val data=input ?: return
        input=null
        runOnUiThread { if(active) { progress.visibility=View.VISIBLE;status.text=if(data.action=="save") "Checking key support and saving… Keep the key steady." else "Reading saved addresses… Keep the key steady." } }
        val result=try {
            val transport=IsoDep.get(tag) ?: error("ISO-DEP required")
            iso=transport;transport.connect()
            val bridge=NomadKeyNfcActivity.ReadBridge(transport,deadline) { active }
            if(!Python.isStarted()) Python.start(AndroidPlatform(this))
            Python.getInstance().getModule("nomadkey.bookmarks").callAttr("android",bridge,data.pin,data.action,data.site).toString()
        } catch(_:Exception) { "" }
        finally { try { iso?.close() } catch(_:Exception) {};iso=null }
        runOnUiThread { finishResult(data.action,result) }
    }
    private fun finishResult(action:String,result:String) {
            if(!active || isFinishing || isDestroyed) return
            active=false;input=null;ui.removeCallbacks(timeout);progress.visibility=View.GONE
            try {
                val response=JSONObject(result)
                if(!response.optBoolean("ok")) { failed(response.optString("message","NFC operation failed."));return }
                val sites=response.getJSONArray("sites");require(sites.length() in 1..16)
                status.text=if(action=="save") "Saved and verified. Move the phone away from your key, then Continue. This does not log you in." else "Addresses read. Move the phone away, then choose a site to open. This does not log you in."
                for(i in 0 until sites.length()) {
                    val site=NomadKeyPins.parse(sites.getJSONObject(i))
                    choices.addView(TextView(this).apply { text="${site.name}\n${site.destination}";setPadding(0,16,0,0) })
                    choices.addView(Button(this).apply {
                        text=if(action=="save") "Continue" else "Open ${site.name}"
                        setOnClickListener {
                            try {
                                if(isFinishing || isDestroyed) return@setOnClickListener
                                done=NomadKeyBookmarkTransfer.complete(generation,site.json().toString()) {
                                    NomadKeyPins.save(this@NomadKeyBookmarkActivity,site)
                                }
                                setResult(if(done) RESULT_OK else RESULT_CANCELED);finish()
                            } catch(_:Exception) { failed("Cannot save this identity locally: it conflicts with a saved site, or local trust data is damaged. Nothing replaced.") }
                        }
                    })
                }
            } catch(_:Exception) { failed("NFC operation failed. If saving, read the key before retrying; the save may be incomplete.") }
    }
    private fun failed(message:String) {
        active=false;input=null;ui.removeCallbacks(timeout)
        status.text="Failed\n\n$message\n\nMove the key away before returning."
        progress.visibility=View.GONE;choices.removeAllViews()
        choices.addView(Button(this).apply { text="Return";setOnClickListener { finish() } })
    }
    override fun onPause() {
        active=false;input=null;ui.removeCallbacks(timeout)
        try { iso?.close() } catch(_:Exception) {}
        if(!done) NomadKeyBookmarkTransfer.clear()
        adapter?.disableReaderMode(this);super.onPause()
        if(!done) finish()
    }
    override fun onDestroy() { ui.removeCallbacksAndMessages(null);super.onDestroy() }
    override fun onSaveInstanceState(outState:Bundle) {}
}
