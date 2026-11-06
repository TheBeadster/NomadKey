package network.columba.app.rns.backend.py

import android.app.Activity
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.IsoDep
import android.view.View
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Button
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import network.columba.app.rns.api.NomadKeyCeremony
import java.util.concurrent.atomic.AtomicBoolean

/** Direct CTAP prompt; retain reader mode until the user confirms the key is away. */
class NomadKeyNfcActivity : Activity(), NfcAdapter.ReaderCallback {
    private var input: NomadKeyCeremony.Input? = null
    private var iso: IsoDep? = null
    private var adapter: NfcAdapter? = null
    private val busy = AtomicBoolean(false)
    private val ui = Handler(Looper.getMainLooper())
    private lateinit var status: TextView
    private lateinit var continueButton: Button
    private var waitingForRemoval = false
    @Volatile private var done = false
    private val removalTimeout = Runnable {
        if (waitingForRemoval) {
            waitingForRemoval = false
            NomadKeyCeremony.clear()
            setResult(RESULT_CANCELED)
            status.text = "Authentication timed out. Move the phone away from your key, then tap below to close. Please try again from the site."
            continueButton.setOnClickListener { finish() }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(null)
        window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        input = NomadKeyCeremony.takeInput()
        if (input == null) { finish(); return }
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(48,48,48,48) }
        layout.addView(TextView(this).apply { text = "Authenticate with NFC key"; textSize = 22f })
        status = TextView(this).apply {
            text = "Hold your Flex or YubiKey at the NFC antenna. When prompted, move the phone away from the key."
            setPadding(0,24,0,24)
        }
        layout.addView(status)
        continueButton = Button(this).apply { text = "Key is away — return to site"; visibility = View.GONE }
        layout.addView(continueButton)
        layout.addView(Button(this).apply { text = "Cancel"; setOnClickListener { finish() } })
        setContentView(layout)
        adapter = NfcAdapter.getDefaultAdapter(this)
        if (adapter?.isEnabled != true) { setResult(RESULT_CANCELED); finish() }
    }

    override fun onResume() {
        super.onResume()
        adapter?.enableReaderMode(this, this,
            NfcAdapter.FLAG_READER_NFC_A or NfcAdapter.FLAG_READER_NFC_B or NfcAdapter.FLAG_READER_SKIP_NDEF_CHECK, null)
    }

    override fun onTagDiscovered(tag: Tag) {
        if (!busy.compareAndSet(false, true)) return
        val data = input ?: return
        input = null
        val generation = data.generation
        val result = try {
            val transport = IsoDep.get(tag) ?: error("ISO-DEP required")
            iso = transport
            transport.connect()
            transport.timeout = 10000
            if (!Python.isStarted()) Python.start(AndroidPlatform(this))
            Python.getInstance().getModule("nomadkey.browser")
                .callAttr("sign", NomadKeyActivity.NfcBridge(transport), data.pin, data.request).toString()
        } catch (_: Exception) {
            null // No PIN retry, exception detail, assertion or secret logging.
        } finally {
            try { iso?.close() } catch (_: Exception) {}
        }
        runOnUiThread {
            if (!isFinishing && !isDestroyed) awaitTagRemoval(tag, generation, result)
        }
    }

    private fun awaitTagRemoval(tag: Tag, generation: Long, assertion: String?) {
        val hasAssertion = assertion != null
        if (assertion != null && !NomadKeyCeremony.stageResponse(generation, assertion)) {
            finish()
            return
        }
        waitingForRemoval = true
        status.text = if (assertion != null)
            "Key read. Move your phone away from Flex (or remove your YubiKey), then tap below to return to the site. NFC website opening stays suppressed while this screen is open."
        else "Key authentication failed. Move your phone away from the key, then tap below to return. No automatic PIN retry."
        // A removal callback can follow intermittent RF contact. Never use it
        // to finish automatically: keep SKIP_NDEF_CHECK until explicit confirmation.
        val released = {
            if (waitingForRemoval && !isFinishing && !isDestroyed) {
                waitingForRemoval = false
                ui.removeCallbacks(removalTimeout)
                done = hasAssertion && NomadKeyCeremony.tagRemoved(generation)
                setResult(if (done) RESULT_OK else RESULT_CANCELED)
                finish()
            }
        }
        continueButton.visibility = View.VISIBLE
        continueButton.setOnClickListener { released() }
        ui.postDelayed(removalTimeout, 20000)
        val removalRegistered = try {
            adapter?.ignore(tag, 1000, {
                if (waitingForRemoval && !isFinishing && !isDestroyed) {
                    status.append("\n\nKey left NFC range. Keep it away until you have returned to the site.")
                }
            }, ui) == true
        } catch (_: Exception) { false }
        if (!removalRegistered) {
            // false also means already removed. Never assume physical removal
            // when the NFC service cannot confirm it; retain reader mode until
            // the user explicitly confirms the key is away.
            status.append("\n\nRemoval could not be confirmed. Move the key away, then tap below.")
        }
    }

    override fun onPause() {
        waitingForRemoval = false
        ui.removeCallbacks(removalTimeout)
        input = null
        if (!done) NomadKeyCeremony.clear()
        try { iso?.close() } catch (_: Exception) {}
        adapter?.disableReaderMode(this)
        super.onPause()
        if (!done) finish()
    }

    override fun onDestroy() {
        ui.removeCallbacksAndMessages(null)
        super.onDestroy()
    }

    override fun onSaveInstanceState(outState: Bundle) { }
}
