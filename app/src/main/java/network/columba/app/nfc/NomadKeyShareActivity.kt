package network.columba.app.nfc

import android.app.Activity
import android.content.Intent
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.Ndef
import android.nfc.tech.IsoDep
import android.nfc.tech.TagTechnology
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import java.util.concurrent.atomic.AtomicBoolean

/** Explicit foreground NDEF workflow. Never invokes CTAP, requests a PIN or saves trust. */
class NomadKeyShareActivity : Activity(),NfcAdapter.ReaderCallback {
    private val ui=Handler(Looper.getMainLooper())
    private val busy=AtomicBoolean(false)
    @Volatile private var active=true
    @Volatile private var transport:TagTechnology?=null
    private var deadline=0L
    private var destination:String?=null
    private var adapter:NfcAdapter?=null
    private lateinit var status:TextView
    private lateinit var progress:ProgressBar
    private lateinit var button:Button
    private val timeout=Runnable {
        if(active) {
            active=false
            try { transport?.close() } catch(_:Exception) {}
            showFailure("Timed out. If writing, read the tag before retrying; the write may be incomplete.")
        }
    }

    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(null)
        if(savedInstanceState!=null) { finish();return }
        val action=intent.getStringExtra("action")
        if(action !in setOf("read","write")) { finish();return }
        if(action=="write") {
            destination=runCatching { NomadKeySharedAddress.validate(intent.getStringExtra("destination").orEmpty()) }.getOrNull()
            if(destination==null) { finish();return }
        }
        deadline=SystemClock.elapsedRealtime()+30000
        val padding=(24*resources.displayMetrics.density).toInt()
        val layout=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(padding,padding,padding,padding) }
        layout.addView(TextView(this).apply { text=if(destination==null) "Read NFC address" else "Save site to NFC";textSize=22f })
        status=TextView(this).apply {
            text=if(destination==null) "Present a card, sticker, Flex or YubiKey. Normal tags need no PIN; security keys use protected storage."
                else "Present a blank NFC tag or your security key. A normal tag gets a public address; a FIDO key will ask for its PIN first."
            setPadding(0,padding,0,padding);accessibilityLiveRegion=View.ACCESSIBILITY_LIVE_REGION_POLITE
        }
        progress=ProgressBar(this).apply { visibility=View.GONE }
        button=Button(this).apply { text="Cancel";setOnClickListener { finish() } }
        layout.addView(status);layout.addView(progress);layout.addView(button)
        setContentView(ScrollView(this).apply { addView(layout) })
        adapter=NfcAdapter.getDefaultAdapter(this)
        if(adapter?.isEnabled!=true) showFailure("Enable NFC, then try again.")
        else ui.postDelayed(timeout,30000)
    }

    override fun onResume() {
        super.onResume()
        if(adapter?.isEnabled==true) adapter?.enableReaderMode(this,this,
            NfcAdapter.FLAG_READER_NFC_A or NfcAdapter.FLAG_READER_NFC_B or
                NfcAdapter.FLAG_READER_NFC_F or NfcAdapter.FLAG_READER_NFC_V,null)
        // Do not use SKIP_NDEF_CHECK: Android must discover the Ndef technology.
    }

    private fun checkLive() { check(active && SystemClock.elapsedRealtime()<deadline) { "Operation ended" } }

    private fun isFido(tag:Tag):Boolean {
        val iso=IsoDep.get(tag) ?: return false
        transport=iso
        try {
            checkLive();iso.connect();iso.timeout=2000;checkLive()
            // Standard FIDO NFC application selection, identical to the SDK transport.
            val command="00a4040008a0000006472f000100".chunked(2).map { it.toInt(16).toByte() }.toByteArray()
            val response=iso.transceive(command)
            require(response.size in 2..128)
            val status=((response[response.size-2].toInt() and 255) shl 8) or (response.last().toInt() and 255)
            return when(status) {
                0x9000 -> true // FIDO/U2F applet present: protected path only, never NDEF fallback.
                0x6a82 -> false // Applet explicitly not found.
                else -> error("Ambiguous FIDO detection")
            }
        } finally { try { iso.close() } catch(_:Exception) {};transport=null }
    }

    override fun onTagDiscovered(tag:Tag) {
        if(!active || !busy.compareAndSet(false,true)) return
        runOnUiThread { if(active) { progress.visibility=View.VISIBLE;status.text="Checking tag type... Keep it steady." } }
        var failure="Could not safely identify the tag. Nothing written. Move it away and try again."
        var fido=false
        val result=try {
            checkLive()
            if(isFido(tag)) {
                fido=true
                ""
            } else {
                val ndef=Ndef.get(tag)
                if(ndef==null) {
                    failure="This tag is not NDEF-formatted or is unsupported. Use a compatible NDEF card or sticker."
                    error("Unsupported tag")
                }
                transport=ndef;checkLive();ndef.connect();checkLive()
                val existing=ndef.ndefMessage
                val target=destination
                if(target==null) {
                    failure="This tag does not contain a supported shared NomadNet landing address."
                    NomadKeySharedAddress.read(existing)
                } else {
                    val wanted=NomadKeySharedAddress.message(target)
                    failure="This tag already contains data. Nothing overwritten. Use a blank tag."
                    require(NomadKeySharedAddress.canWrite(existing,target))
                    if(NomadKeySharedAddress.blank(existing)) {
                        failure="This tag is read-only or too small. Nothing written."
                        require(ndef.isWritable && ndef.maxSize>=wanted.toByteArray().size)
                        checkLive()
                        failure="Write could not be verified. Read the tag before retrying; it may be incomplete."
                        ndef.writeNdefMessage(wanted)
                    }
                    checkLive()
                    failure="Write readback failed. Read the tag before retrying."
                    require(NomadKeySharedAddress.read(ndef.ndefMessage)==target)
                    target
                }
            }
        } catch(_:Exception) { null }
        finally { try { transport?.close() } catch(_:Exception) {};transport=null }
        runOnUiThread { if(fido && result!=null) finishFido() else finishRead(result,failure) }
    }

    private fun finishFido() {
        if(!active || isFinishing || isDestroyed) return
        if(SystemClock.elapsedRealtime()>=deadline) { showFailure("Detection timed out. Nothing written.");return }
        active=false;ui.removeCallbacks(timeout);progress.visibility=View.GONE
        status.text="Security key detected\n\nMove the key away, then Continue to enter its FIDO2 PIN. Present it again when asked. Nothing has been written."
        button.text="Continue"
        button.setOnClickListener {
            if(!isFinishing && !isDestroyed) {
                setResult(RESULT_OK,Intent().putExtra("kind","fido"));finish()
            }
        }
    }

    private fun finishRead(result:String?,failure:String) {
        if(!active || isFinishing || isDestroyed) return
        if(SystemClock.elapsedRealtime()>=deadline) { showFailure("Timed out. Read the tag before retrying a write.");return }
        if(result==null) { showFailure(failure);return }
        active=false;ui.removeCallbacks(timeout);progress.visibility=View.GONE
        val writing=destination!=null
        status.text=if(writing) "Success: address verified on tag.\n\n$result\n\nMove the tag away, then Continue. Anyone can read this public address."
            else "Shared address — not verified\n\n$result\n\nMove the tag away, then Open site. This does not save trust or log you in."
        button.text=if(writing) "Continue" else "Open site"
        button.setOnClickListener {
            if(!isFinishing && !isDestroyed) {
                setResult(RESULT_OK,Intent().putExtra("kind","public").putExtra("destination",result));finish()
            }
        }
    }

    private fun showFailure(message:String) {
        active=false;ui.removeCallbacks(timeout);progress.visibility=View.GONE
        status.text="Failed\n\n$message\n\nMove the tag away before returning."
        button.text="Return";button.setOnClickListener { finish() }
    }

    override fun onPause() {
        active=false;ui.removeCallbacks(timeout)
        try { transport?.close() } catch(_:Exception) {}
        adapter?.disableReaderMode(this);super.onPause();finish()
    }
    override fun onDestroy() { ui.removeCallbacksAndMessages(null);super.onDestroy() }
    override fun onSaveInstanceState(outState:Bundle) {}
}
