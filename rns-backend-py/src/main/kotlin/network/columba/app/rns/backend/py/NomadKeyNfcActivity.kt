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
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Button
import android.widget.ProgressBar
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import network.columba.app.rns.api.NomadKeyCeremony
import java.io.IOException
import java.util.concurrent.atomic.AtomicBoolean

/** Bounded NFC reads. Reader mode stays active until an explicit user handoff. */
class NomadKeyNfcActivity : Activity(), NfcAdapter.ReaderCallback {
    private var input: NomadKeyCeremony.Input? = null
    @Volatile private var iso: IsoDep? = null
    private var adapter: NfcAdapter? = null
    private val busy = AtomicBoolean(false)
    private val ui = Handler(Looper.getMainLooper())
    private lateinit var status: TextView
    private lateinit var detail: TextView
    private lateinit var progress: ProgressBar
    private lateinit var continueButton: Button
    private var deadline = 0L
    @Volatile private var accepting = false
    private var succeeded = false
    @Volatile private var done = false
    private var generation = 0L

    private val tick = object : Runnable {
        override fun run() {
            if (!accepting) return
            val remaining = deadline - SystemClock.elapsedRealtime()
            if (remaining <= 0) {
                fail("No complete key read within 15 seconds. Move the phone away, then return to the page to try again.")
            } else {
                progress.progress = (15000 - remaining).toInt().coerceIn(0, 15000)
                ui.postDelayed(this, 100)
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(null)
        window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        input = NomadKeyCeremony.takeInput()
        val data = input ?: run { finish(); return }
        generation = data.generation
        deadline = SystemClock.elapsedRealtime() + 15000
        accepting = true
        val padding = (24 * resources.displayMetrics.density).toInt()
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
        }
        status = TextView(this).apply { text = "Present key"; textSize = 26f; accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE }
        detail = TextView(this).apply {
            text = "Hold your Flex or YubiKey against the NFC antenna. You have 15 seconds."
            setPadding(0, padding, 0, padding)
        }
        progress = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 15000; visibility = View.GONE
            contentDescription = "Authenticating; 15 second attempt"
        }
        continueButton = Button(this).apply { visibility = View.GONE }
        layout.addView(status); layout.addView(detail); layout.addView(progress); layout.addView(continueButton)
        layout.addView(Button(this).apply { text = "Cancel"; setOnClickListener { finish() } })
        setContentView(ScrollView(this).apply { addView(layout) })
        adapter = NfcAdapter.getDefaultAdapter(this)
        if (adapter?.isEnabled != true) fail("NFC is unavailable. Enable NFC, then return to the page to try again.")
        else ui.post(tick)
    }

    override fun onResume() {
        super.onResume()
        if (adapter?.isEnabled == true) adapter?.enableReaderMode(this, this,
            NfcAdapter.FLAG_READER_NFC_A or NfcAdapter.FLAG_READER_NFC_B or NfcAdapter.FLAG_READER_SKIP_NDEF_CHECK, null)
    }

    override fun onTagDiscovered(tag: Tag) {
        if (!accepting || !busy.compareAndSet(false, true)) return
        val data = input ?: run { busy.set(false); return }
        runOnUiThread {
            if (accepting) {
                status.text = "Authenticating…"
                detail.text = "Key detected. Keep it steady against the phone."
                progress.visibility = View.VISIBLE
            }
        }
        var bridge: ReadBridge? = null
        var disconnected = false
        val result = try {
            if (!accepting || SystemClock.elapsedRealtime() >= deadline) throw IOException()
            val transport = IsoDep.get(tag) ?: error("ISO-DEP required")
            iso = transport
            transport.connect()
            bridge = ReadBridge(transport, deadline) { accepting }
            if (!Python.isStarted()) Python.start(AndroidPlatform(this))
            Python.getInstance().getModule("nomadkey.browser")
                .callAttr("sign", bridge, data.pin, data.request).toString()
        } catch (_: IOException) {
            disconnected = true
            null
        } catch (_: Exception) {
            // Only an observed transport I/O failure is retryable. In particular,
            // a CTAP PIN rejection must not trigger another PIN attempt.
            disconnected = bridge?.contactLost == true
            null
        } finally {
            try { iso?.close() } catch (_: Exception) {}
            iso = null
        }
        runOnUiThread { finishRead(result, disconnected) }
    }

    private fun finishRead(assertion: String?, disconnected: Boolean) {
        busy.set(false)
        if (!accepting || isFinishing || isDestroyed) return
        if (SystemClock.elapsedRealtime() >= deadline) {
            fail("No complete key read within 15 seconds. Move the phone away, then try again from the page.")
        } else if (assertion != null && NomadKeyCeremony.stageResponse(generation, assertion)) {
            accepting = false; succeeded = true; input = null
            ui.removeCallbacks(tick)
            progress.visibility = View.GONE
            status.text = "Success"
            detail.text = "Key read successfully. Move the phone away from your key, then continue to finish signing in to the site."
            continueButton.text = "Continue"
            continueButton.visibility = View.VISIBLE
            continueButton.setOnClickListener {
                if (succeeded && !isFinishing) {
                    done = NomadKeyCeremony.tagRemoved(generation)
                    setResult(if (done) RESULT_OK else RESULT_CANCELED)
                    finish()
                }
            }
        } else if (disconnected) {
            status.text = "Authenticating…"
            detail.text = "Contact lost. Hold the key against the phone again. Retrying within the same 15 seconds."
            progress.visibility = View.VISIBLE
        } else {
            fail("The key could not authenticate. Check your key and PIN, then return to the page to try again.")
        }
    }

    private fun fail(message: String) {
        accepting = false; succeeded = false; input = null
        ui.removeCallbacks(tick)
        NomadKeyCeremony.clear()
        try { iso?.close() } catch (_: Exception) {}
        status.text = "Failed"
        detail.text = message
        progress.visibility = View.GONE
        continueButton.text = "Try again"
        continueButton.visibility = View.VISIBLE
        continueButton.setOnClickListener { setResult(RESULT_CANCELED); finish() }
    }

    /** Keep Java I/O classification across the Python boundary without parsing errors. */
    class ReadBridge(private val transport: IsoDep, private val deadline: Long, private val active: () -> Boolean) {
        @Volatile var contactLost = false
            private set
        fun transceive(data: ByteArray): ByteArray {
            val remaining = deadline - SystemClock.elapsedRealtime()
            if (!active() || remaining <= 0) throw IOException("NFC attempt ended")
            try {
                transport.timeout = remaining.coerceIn(1, 10000).toInt()
                return transport.transceive(data)
            } catch (e: IOException) {
                contactLost = true
                throw e
            }
        }
        fun close() { try { transport.close() } catch (_: Exception) {} }
    }

    override fun onPause() {
        accepting = false; succeeded = false; input = null
        ui.removeCallbacks(tick)
        if (!done) NomadKeyCeremony.clear()
        try { iso?.close() } catch (_: Exception) {}
        adapter?.disableReaderMode(this)
        super.onPause()
        if (!done) finish()
    }

    override fun onDestroy() { ui.removeCallbacksAndMessages(null); super.onDestroy() }
    override fun onSaveInstanceState(outState: Bundle) { }
}
