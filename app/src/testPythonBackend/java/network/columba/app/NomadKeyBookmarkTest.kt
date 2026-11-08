package network.columba.app

import android.app.Activity
import android.app.Application
import android.nfc.NfcAdapter
import android.os.Looper
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import io.mockk.*
import network.columba.app.rns.api.NomadKeyBookmarkTransfer
import network.columba.app.rns.api.NomadKeyPins
import org.json.JSONArray
import org.json.JSONObject
import org.junit.*
import org.junit.Assert.*
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.android.controller.ActivityController
import java.io.File
import java.time.Duration

/** Software-only UI, persistence and cancellation checks; no NFC hardware. */
@RunWith(RobolectricTestRunner::class)
@Config(application = Application::class, sdk = [35])
class NomadKeyBookmarkTest {
    private val adapter=mockk<NfcAdapter>(relaxed=true)
    private lateinit var controller:ActivityController<Activity>
    private lateinit var activity:Activity
    @Suppress("UNCHECKED_CAST")
    private val type=Class.forName("network.columba.app.rns.backend.py.NomadKeyBookmarkActivity") as Class<Activity>
    private val site=NomadKeyPins.Site("11".repeat(16),"22".repeat(64),"Test site")
    @Before fun setup() {
        mockkStatic(NfcAdapter::class)
        every { NfcAdapter.getDefaultAdapter(any()) } returns adapter
        every { adapter.isEnabled } returns true
        NomadKeyBookmarkTransfer.prepare("read","software-pin")
        controller=Robolectric.buildActivity(type).create().start().resume()
        activity=controller.get()
        File(activity.noBackupFilesDir,"nomadkey-trusted-sites.json").delete()
    }
    @After fun cleanup() {
        controller.pause().stop().destroy()
        NomadKeyBookmarkTransfer.clear()
        unmockkAll()
    }
    private fun field(name:String)=type.getDeclaredField(name).apply { isAccessible=true }.get(activity)
    private fun result(action:String="read",sites:List<NomadKeyPins.Site> = listOf(site)) {
        val array=JSONArray();sites.forEach { array.put(it.json()) }
        type.getDeclaredMethod("finishResult",String::class.java,String::class.java).apply { isAccessible=true }
            .invoke(activity,action,JSONObject().put("ok",true).put("sites",array).toString())
    }
    private fun button(index:Int=1)=(field("choices") as LinearLayout).getChildAt(index) as Button
    private fun status()=(field("status") as TextView).text.toString()
    @Test fun readWaitsForSelectionAndKeepsNdefSuppressed() {
        result()
        assertTrue(status().startsWith("Addresses read"))
        assertTrue(NomadKeyPins.all(activity).isEmpty())
        assertNull(NomadKeyBookmarkTransfer.takeResult())
        verify(exactly=0) { adapter.disableReaderMode(any()) }
        button().performClick()
        assertEquals(listOf(site),NomadKeyPins.all(activity))
        assertEquals(Activity.RESULT_OK,shadowOf(activity).resultCode)
        assertNotNull(NomadKeyBookmarkTransfer.takeResult())
    }
    @Test fun onlySelectedSiteIsImported() {
        val second=site.copy(destination="33".repeat(16),name="Other")
        result(sites=listOf(site,second));button(3).performClick()
        assertEquals(listOf(second),NomadKeyPins.all(activity))
    }
    @Test fun saveRequiresContinue() {
        result("save")
        assertEquals("Continue",button().text.toString())
        assertTrue(NomadKeyPins.all(activity).isEmpty())
        button().performClick();assertEquals(site,NomadKeyPins.find(activity,site.destination))
    }
    @Test fun timeoutRejectsLateSuccess() {
        shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(60))
        assertTrue(status().startsWith("Failed"))
        result();assertTrue(status().startsWith("Failed"))
        assertTrue(NomadKeyPins.all(activity).isEmpty())
    }
    @Test fun cancelledGenerationCannotImportFromOldButton() {
        result();NomadKeyBookmarkTransfer.clear();button().performClick()
        assertTrue(NomadKeyPins.all(activity).isEmpty())
        assertEquals(Activity.RESULT_CANCELED,shadowOf(activity).resultCode)
    }
    @Test fun pausePreventsImportAndLateResult() {
        result();controller.pause();button().performClick();result()
        assertTrue(NomadKeyPins.all(activity).isEmpty())
        assertNull(NomadKeyBookmarkTransfer.takeResult())
    }
    @Test fun savedPinRejectsDifferentPublicKeyWithoutReplacement() {
        NomadKeyPins.save(activity,site)
        assertThrows(IllegalArgumentException::class.java) { NomadKeyPins.save(activity,site.copy(publicKey="44".repeat(64))) }
        assertThrows(IllegalArgumentException::class.java) { NomadKeyPins.verify(activity,site.destination,"44".repeat(64)) }
        NomadKeyPins.verify(activity,site.destination,site.publicKey)
        assertEquals(site,NomadKeyPins.find(activity,site.destination))
    }
    @Test fun sameNameDifferentDestinationCannotReplaceTrustedSite() {
        NomadKeyPins.save(activity,site)
        assertThrows(IllegalArgumentException::class.java) { NomadKeyPins.save(activity,site.copy(destination="55".repeat(16))) }
        assertEquals(listOf(site),NomadKeyPins.all(activity))
    }
    @Test fun malformedOrOversizedStoreFailsClosed() {
        val file=File(activity.noBackupFilesDir,"nomadkey-trusted-sites.json")
        file.writeText("bad")
        assertThrows(Exception::class.java) { NomadKeyPins.verify(activity,site.destination,site.publicKey) }
        file.writeText("x".repeat(16385))
        assertThrows(IllegalArgumentException::class.java) { NomadKeyPins.all(activity) }
    }
    @Test fun repeatedImportIsIdempotent() {
        NomadKeyPins.save(activity,site);NomadKeyPins.save(activity,site)
        assertEquals(listOf(site),NomadKeyPins.all(activity))
    }
}
