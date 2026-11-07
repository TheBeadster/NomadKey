package network.columba.app

import android.app.Activity
import android.app.Application
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.IsoDep
import android.os.Looper
import android.os.SystemClock
import android.view.View
import android.widget.Button
import android.widget.TextView
import android.widget.ProgressBar
import io.mockk.*
import network.columba.app.rns.api.NomadKeyCeremony
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.Assert.*
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.android.controller.ActivityController
import java.time.Duration
import java.io.IOException

/** Software lifecycle and transport tests; no physical NFC hardware is exercised. */
@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class, sdk = [35])
class NomadKeyNfcHandoffTest {
    private val adapter = mockk<NfcAdapter>(relaxed = true)
    private lateinit var controller: ActivityController<Activity>
    private lateinit var activity: Activity
    @Suppress("UNCHECKED_CAST")
    private val activityType = Class.forName("network.columba.app.rns.backend.py.NomadKeyNfcActivity") as Class<Activity>

    @Before fun setup() {
        mockkStatic(NfcAdapter::class)
        every { NfcAdapter.getDefaultAdapter(any()) } returns adapter
        every { adapter.isEnabled } returns true
        NomadKeyCeremony.prepare("software-request", "software-pin")
        controller = Robolectric.buildActivity(activityType).create().start().resume()
        activity = controller.get()
    }

    private fun field(name: String): Any? = activityType.getDeclaredField(name).apply { isAccessible = true }.get(activity)
    private fun status() = (field("status") as TextView).text.toString()
    private fun button() = field("continueButton") as Button
    private fun result(assertion: String? = "software-assertion", disconnected: Boolean = false) {
        activityType.getDeclaredMethod("finishRead", String::class.java, java.lang.Boolean.TYPE)
            .apply { isAccessible = true }.invoke(activity, assertion, disconnected)
    }
    private fun advance(seconds: Long) = shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(seconds))

    @After fun cleanup() {
        if (::controller.isInitialized) controller.pause().stop().destroy()
        NomadKeyCeremony.clear()
        unmockkAll()
    }

    @Test fun successRequiresContinueAndKeepsReaderActive() {
        result()
        assertEquals("Success", status())
        assertEquals("Continue", button().text.toString())
        assertNull(field("input"))
        assertFalse(activity.isFinishing)
        assertNull(NomadKeyCeremony.takeResponse())
        verify(exactly = 0) { adapter.disableReaderMode(any()) }
        advance(16)
        assertEquals("Success", status())
        button().performClick()
        assertTrue(activity.isFinishing)
        assertEquals(Activity.RESULT_OK, shadowOf(activity).resultCode)
        assertEquals("software-assertion", NomadKeyCeremony.takeResponse())
    }

    @Test fun actualConnectBounceShowsProgressAndPreservesInputForRetap() {
        mockkStatic(IsoDep::class)
        val tag = mockk<Tag>()
        val iso = mockk<IsoDep>(relaxed = true)
        every { IsoDep.get(tag) } returns iso
        every { iso.connect() } throws IOException("simulated loss")
        (activity as NfcAdapter.ReaderCallback).onTagDiscovered(tag)
        assertEquals("Authenticating…", status())
        assertEquals(View.VISIBLE, (field("progress") as ProgressBar).visibility)
        assertNotNull(field("input"))
        assertFalse(activity.isFinishing)
        (activity as NfcAdapter.ReaderCallback).onTagDiscovered(tag)
        verify(exactly = 2) { iso.connect() }
        result()
        assertEquals("Success", status())
    }

    @Test fun repeatedBouncesDoNotExtendFifteenSecondDeadline() {
        advance(7); result(null, true)
        advance(7); result(null, true)
        assertEquals("Authenticating…", status())
        advance(1)
        assertEquals("Failed", status())
        assertEquals("Try again", button().text.toString())
        assertNull(field("input"))
        assertFalse(activity.isFinishing)
        verify(exactly = 0) { adapter.disableReaderMode(any()) }
        result()
        assertEquals("Failed", status())
        button().performClick()
        assertEquals(Activity.RESULT_CANCELED, shadowOf(activity).resultCode)
        assertNull(NomadKeyCeremony.takeResponse())
    }

    @Test fun noKeyTimesOutAndTryAgainReturnsToPage() {
        assertEquals("Present key", status())
        advance(15)
        assertEquals("Failed", status())
        button().performClick()
        assertTrue(activity.isFinishing)
        assertEquals(Activity.RESULT_CANCELED, shadowOf(activity).resultCode)
    }

    @Test fun successJustBeforeDeadlineIsAccepted() {
        advance(14); result(); advance(1)
        assertEquals("Success", status())
        button().performClick()
        assertEquals(Activity.RESULT_OK, shadowOf(activity).resultCode)
    }

    @Test fun timeoutClosesActiveTransport() {
        val iso = mockk<IsoDep>(relaxed = true)
        activityType.getDeclaredField("iso").apply { isAccessible = true }.set(activity, iso)
        advance(15)
        verify { iso.close() }
        assertEquals("Failed", status())
    }

    @Test fun protocolOrPinFailureDoesNotAutomaticallyRetry() {
        result(null, false)
        assertEquals("Failed", status())
        assertNull(field("input"))
        (activity as NfcAdapter.ReaderCallback).onTagDiscovered(mockk<Tag>())
        result()
        assertEquals("Failed", status())
        assertNull(NomadKeyCeremony.takeResponse())
    }

    @Test fun backgroundRejectsLateReadAndClearsPendingSuccess() {
        result()
        controller.pause()
        result()
        button().performClick()
        assertEquals(Activity.RESULT_CANCELED, shadowOf(activity).resultCode)
        assertNull(NomadKeyCeremony.takeResponse())
    }

    @Test fun staleCeremonyCannotBecomeSuccess() {
        NomadKeyCeremony.clear()
        result()
        assertEquals("Failed", status())
        assertNull(NomadKeyCeremony.takeResponse())
    }

    @Test fun bridgeClassifiesIoFailureAcrossPythonBoundary() {
        val type = Class.forName("network.columba.app.rns.backend.py.NomadKeyNfcActivity\$ReadBridge")
        val iso = mockk<IsoDep>(relaxed = true)
        every { iso.transceive(any()) } throws IOException("simulated RF loss")
        val active: () -> Boolean = { true }
        val bridge = type.declaredConstructors.single().newInstance(iso, SystemClock.elapsedRealtime() + 15000, active)
        assertThrows(java.lang.reflect.InvocationTargetException::class.java) {
            type.getMethod("transceive", ByteArray::class.java).invoke(bridge, byteArrayOf(0))
        }
        assertEquals(true, type.getMethod("getContactLost").invoke(bridge))
    }

    @Test fun bridgeRejectsIoAfterDeadlineWithoutTransmitting() {
        val type = Class.forName("network.columba.app.rns.backend.py.NomadKeyNfcActivity\$ReadBridge")
        val iso = mockk<IsoDep>(relaxed = true)
        val active: () -> Boolean = { true }
        val bridge = type.declaredConstructors.single().newInstance(iso, SystemClock.elapsedRealtime(), active)
        assertThrows(java.lang.reflect.InvocationTargetException::class.java) {
            type.getMethod("transceive", ByteArray::class.java).invoke(bridge, byteArrayOf(0))
        }
        verify(exactly = 0) { iso.transceive(any()) }
        assertEquals(false, type.getMethod("getContactLost").invoke(bridge))
    }
}
