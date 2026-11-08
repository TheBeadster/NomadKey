package network.columba.app

import android.app.Activity
import android.app.Application
import android.content.Intent
import android.nfc.NdefMessage
import android.nfc.NdefRecord
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.IsoDep
import android.nfc.tech.Ndef
import android.os.Looper
import android.widget.Button
import android.widget.TextView
import io.mockk.*
import network.columba.app.nfc.NomadKeyShareActivity
import network.columba.app.nfc.NomadKeySharedAddress
import network.columba.app.rns.api.NomadKeyPins
import org.junit.*
import org.junit.Assert.*
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.android.controller.ActivityController
import java.io.IOException
import java.time.Duration

/** NDEF/ISO-DEP are simulated. These tests do not establish physical tag compatibility. */
@RunWith(RobolectricTestRunner::class)
@Config(application=Application::class,sdk=[35])
class NomadKeyShareTest {
    private val address="ab".repeat(16)
    private val other="cd".repeat(16)
    private val adapter=mockk<NfcAdapter>(relaxed=true)
    private val ndef=mockk<Ndef>(relaxed=true)
    private val tag=mockk<Tag>()
    private var message:NdefMessage?=null
    private var controller:ActivityController<NomadKeyShareActivity>?=null
    private lateinit var activity:NomadKeyShareActivity
    @Before fun setup() {
        mockkStatic(NfcAdapter::class,Ndef::class,IsoDep::class)
        every { NfcAdapter.getDefaultAdapter(any()) } returns adapter
        every { adapter.isEnabled } returns true
        every { Ndef.get(tag) } returns ndef
        every { IsoDep.get(tag) } returns null
        every { ndef.ndefMessage } answers { message }
        every { ndef.maxSize } returns 137
        every { ndef.isWritable } returns true
        every { ndef.writeNdefMessage(any()) } answers { message=firstArg();Unit }
    }
    @After fun cleanup() { controller?.pause()?.stop()?.destroy();unmockkAll() }
    private fun start(write:Boolean=false) {
        val intent=Intent().putExtra("action",if(write) "write" else "read")
        if(write) intent.putExtra("destination",address)
        controller=Robolectric.buildActivity(NomadKeyShareActivity::class.java,intent).create().start().resume()
        activity=controller!!.get()
    }
    private fun field(name:String)=NomadKeyShareActivity::class.java.getDeclaredField(name).apply { isAccessible=true }.get(activity)
    private fun status()=(field("status") as TextView).text.toString()
    private fun click()=(field("button") as Button).performClick()
    private fun scan()=activity.onTagDiscovered(tag)
    private fun securityKey(response:ByteArray):IsoDep {
        val iso=mockk<IsoDep>(relaxed=true)
        every { IsoDep.get(tag) } returns iso
        every { iso.transceive(any()) } returns response
        return iso
    }

    @Test fun publicRecordRoundTripFitsSmallTagsAndContainsOnlyRootAddress() {
        val encoded=NomadKeySharedAddress.message(address)
        assertTrue(encoded.toByteArray().size<=137)
        assertEquals(address,NomadKeySharedAddress.read(NdefMessage(encoded.toByteArray())))
        assertEquals("nomadnetwork://$address:/page/index.mu",encoded.records.single().toUri().toString())
    }
    @Test fun alternatePathsQueriesExternalUrisAndMalformedAddressesRejected() {
        for(uri in listOf("https://example.com", "nomadnetwork://$address:/page/private.mu",
            "nomadnetwork://$address:/page/index.mu?token=abc", "nomadnetwork://$address:/page/index.mu#x",
            "nomadnetwork://user@$address:/page/index.mu", "nomadnetwork://short:/page/index.mu")) {
            assertThrows(IllegalArgumentException::class.java) { NomadKeySharedAddress.read(NdefMessage(arrayOf(NdefRecord.createUri(uri)))) }
        }
        assertThrows(IllegalArgumentException::class.java) { NomadKeySharedAddress.message("../bad") }
    }
    @Test fun extraRecordsTextRecordsAndOversizedMessagesRejected() {
        val record=NomadKeySharedAddress.message(address).records.single()
        for(records in listOf(arrayOf(record,record),arrayOf(NdefRecord.createTextRecord("en",address)),
            arrayOf(NdefRecord.createUri("https://example.com/"+"x".repeat(300))))) {
            assertThrows(IllegalArgumentException::class.java) { NomadKeySharedAddress.read(NdefMessage(records)) }
        }
    }
    @Test fun blankNormalTagWritesOnceAndReadsBack() {
        start(true);scan()
        assertTrue(status().startsWith("Success"))
        verify(exactly=1) { ndef.writeNdefMessage(any()) }
        verify(atLeast=2) { ndef.ndefMessage }
        assertEquals(address,NomadKeySharedAddress.read(message))
        assertFalse(activity.isFinishing)
        verify(exactly=0) { adapter.disableReaderMode(any()) }
        click();assertEquals(Activity.RESULT_OK,shadowOf(activity).resultCode)
    }
    @Test fun tnfEmptyTagCanBeWritten() {
        message=NdefMessage(arrayOf(NdefRecord(NdefRecord.TNF_EMPTY,byteArrayOf(),byteArrayOf(),byteArrayOf())))
        start(true);scan();assertTrue(status().startsWith("Success"))
    }
    @Test fun existingWebsiteIsNotOverwritten() {
        message=NdefMessage(arrayOf(NdefRecord.createUri("https://example.com")))
        start(true);scan();assertTrue(status().contains("Nothing overwritten"))
        verify(exactly=0) { ndef.writeNdefMessage(any()) }
    }
    @Test fun existingDifferentSiteIsNotOverwritten() {
        message=NomadKeySharedAddress.message(other)
        start(true);scan();assertTrue(status().startsWith("Failed"))
        verify(exactly=0) { ndef.writeNdefMessage(any()) }
    }
    @Test fun sameAddressIsIdempotentEvenOnReadOnlyTag() {
        message=NomadKeySharedAddress.message(address);every { ndef.isWritable } returns false
        start(true);scan();assertTrue(status().startsWith("Success"))
        verify(exactly=0) { ndef.writeNdefMessage(any()) }
    }
    @Test fun tooSmallTagIsNotWritten() {
        every { ndef.maxSize } returns 10
        start(true);scan();assertTrue(status().contains("too small"))
        verify(exactly=0) { ndef.writeNdefMessage(any()) }
    }
    @Test fun readOnlyBlankTagIsNotWritten() {
        every { ndef.isWritable } returns false
        start(true);scan();assertTrue(status().contains("read-only"))
        verify(exactly=0) { ndef.writeNdefMessage(any()) }
    }
    @Test fun readbackMismatchNeverReportsSuccess() {
        every { ndef.writeNdefMessage(any()) } just Runs
        start(true);scan();assertTrue(status().contains("readback failed"))
        assertEquals(Activity.RESULT_CANCELED,shadowOf(activity).resultCode)
    }
    @Test fun lostWriteIsNeverAutomaticallyRetried() {
        every { ndef.writeNdefMessage(any()) } throws IOException("simulated loss")
        start(true);scan();scan()
        assertTrue(status().startsWith("Failed"))
        verify(exactly=1) { ndef.writeNdefMessage(any()) }
    }
    @Test fun readRequiresOpenAndNeverChangesTrustedPins() {
        message=NomadKeySharedAddress.message(other);start()
        val pin=NomadKeyPins.Site(address,"11".repeat(64),"Trusted")
        NomadKeyPins.save(activity,pin);val before=NomadKeyPins.all(activity)
        scan();assertTrue(status().contains("not verified"))
        assertEquals(Activity.RESULT_CANCELED,shadowOf(activity).resultCode)
        assertEquals(before,NomadKeyPins.all(activity))
        click();assertEquals(other,shadowOf(activity).resultIntent.getStringExtra("destination"))
        assertEquals(before,NomadKeyPins.all(activity))
        verify(exactly=0) { ndef.writeNdefMessage(any()) }
    }
    @Test fun timeoutAndLateDetectionCannotWriteOrOpen() {
        start(true);shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(30));scan()
        assertTrue(status().startsWith("Failed"))
        verify(exactly=0) { ndef.writeNdefMessage(any()) }
        assertEquals(Activity.RESULT_CANCELED,shadowOf(activity).resultCode)
    }
    @Test fun pauseAfterReadCannotOpen() {
        message=NomadKeySharedAddress.message(address);start();scan();controller!!.pause();click()
        assertEquals(Activity.RESULT_CANCELED,shadowOf(activity).resultCode)
    }
    @Test fun fidoTakesPriorityOverNdefAndRequiresProtectedHandoff() {
        message=NdefMessage(arrayOf(NdefRecord.createUri("https://example.com")))
        val iso=securityKey("FIDO_2_0".toByteArray()+byteArrayOf(0x90.toByte(),0))
        start(true);scan()
        assertTrue(status().contains("Security key detected"))
        assertTrue(status().contains("PIN"))
        verify(exactly=0) { Ndef.get(any()) }
        verify(exactly=1) { iso.transceive(any()) }
        click();assertEquals("fido",shadowOf(activity).resultIntent.getStringExtra("kind"))
    }
    @Test fun fidoReadAlsoRoutesToProtectedStorage() {
        securityKey(byteArrayOf(0x90.toByte(),0));start();scan();click()
        assertEquals("fido",shadowOf(activity).resultIntent.getStringExtra("kind"))
        verify(exactly=0) { Ndef.get(any()) }
    }
    @Test fun ambiguousSecurityKeyDetectionNeverFallsBackToPublicWrite() {
        securityKey(byteArrayOf(0x69,0x85.toByte()));start(true);scan()
        assertTrue(status().startsWith("Failed"))
        verify(exactly=0) { Ndef.get(any()) }
    }
    @Test fun failedSecurityKeyProbeNeverFallsBackToPublicWrite() {
        val iso=securityKey(byteArrayOf());every { iso.transceive(any()) } throws IOException("lost")
        start(true);scan();assertTrue(status().startsWith("Failed"))
        verify(exactly=0) { Ndef.get(any()) }
    }
    @Test fun ordinaryTypeFourTagWithNoFidoAppletUsesNdef() {
        securityKey(byteArrayOf(0x6a,0x82.toByte()));start(true);scan()
        assertTrue(status().startsWith("Success"))
        verify(exactly=1) { ndef.writeNdefMessage(any()) }
    }
    @Test fun unsupportedTagIsNotFormattedOrWritten() {
        every { Ndef.get(tag) } returns null
        start(true);scan();assertTrue(status().contains("not NDEF-formatted"))
        verify(exactly=0) { ndef.writeNdefMessage(any()) }
    }
}
