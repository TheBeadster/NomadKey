package network.columba.app

import android.app.Activity
import android.app.Application
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.os.Looper
import android.widget.Button
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

/** Android lifecycle and removal callbacks are simulated; no NFC hardware is exercised. */
@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class, sdk = [35])
class NomadKeyNfcHandoffTest {
    private val adapter = mockk<NfcAdapter>(relaxed = true)
    private val listener = slot<NfcAdapter.OnTagRemovedListener>()
    private lateinit var controller: ActivityController<Activity>
    private lateinit var activity: Activity
    @Suppress("UNCHECKED_CAST")
    private val activityType = Class.forName("network.columba.app.rns.backend.py.NomadKeyNfcActivity") as Class<Activity>
    private var generation = 0L

    @Before fun setup() {
        mockkStatic(NfcAdapter::class)
        every { NfcAdapter.getDefaultAdapter(any()) } returns adapter
        every { adapter.isEnabled } returns true
        every { adapter.ignore(any(), 1000, capture(listener), any()) } returns true
        NomadKeyCeremony.prepare("software-request", "software-pin")
        controller = Robolectric.buildActivity(activityType).create().start().resume()
        activity = controller.get()
        val field = activityType.getDeclaredField("input").apply { isAccessible = true }
        generation = (field.get(activity) as NomadKeyCeremony.Input).generation
    }

    private fun keyRead(assertion: String? = "software-assertion") {
        val method = activityType.getDeclaredMethod(
            "awaitTagRemoval", Tag::class.java, java.lang.Long.TYPE, String::class.java,
        ).apply { isAccessible = true }
        method.invoke(activity, mockk<Tag>(), generation, assertion)
    }

    @After fun cleanup() {
        if (::controller.isInitialized) controller.pause().stop().destroy()
        NomadKeyCeremony.clear()
        unmockkStatic(NfcAdapter::class)
        clearAllMocks()
    }

    @Test fun keyReadKeepsReaderActiveUntilRemoval() {
        keyRead()
        assertFalse(activity.isFinishing)
        assertNull(NomadKeyCeremony.takeResponse())
        verify(exactly = 0) { adapter.disableReaderMode(any()) }
        listener.captured.onTagRemoved()
        assertTrue(activity.isFinishing)
        assertEquals(Activity.RESULT_OK, shadowOf(activity).resultCode)
        assertEquals("software-assertion", NomadKeyCeremony.takeResponse())
    }

    @Test fun backgroundBeforeRemovalCancelsAndRejectsLateCallback() {
        keyRead()
        controller.pause()
        listener.captured.onTagRemoved()
        assertTrue(activity.isFinishing)
        assertEquals(Activity.RESULT_CANCELED, shadowOf(activity).resultCode)
        assertNull(NomadKeyCeremony.takeResponse())
    }

    @Test fun removalTimeoutCancelsInsteadOfAuthorizing() {
        keyRead()
        shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(20))
        listener.captured.onTagRemoved()
        assertTrue(activity.isFinishing)
        assertEquals(Activity.RESULT_CANCELED, shadowOf(activity).resultCode)
        assertNull(NomadKeyCeremony.takeResponse())
    }

    @Test fun unavailableRemovalDetectionRequiresExplicitConfirmation() {
        every { adapter.ignore(any(), 1000, any(), any()) } returns false
        keyRead()
        assertFalse(activity.isFinishing)
        assertNull(NomadKeyCeremony.takeResponse())
        val field = activityType.getDeclaredField("continueButton").apply { isAccessible = true }
        (field.get(activity) as Button).performClick()
        assertEquals(Activity.RESULT_OK, shadowOf(activity).resultCode)
        assertEquals("software-assertion", NomadKeyCeremony.takeResponse())
    }

    @Test fun failedKeyReadWaitsForRemovalButReturnsNoAssertion() {
        keyRead(null)
        assertFalse(activity.isFinishing)
        listener.captured.onTagRemoved()
        assertEquals(Activity.RESULT_CANCELED, shadowOf(activity).resultCode)
        assertNull(NomadKeyCeremony.takeResponse())
    }
}
