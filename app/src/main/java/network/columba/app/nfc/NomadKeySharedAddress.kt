package network.columba.app.nfc

import android.nfc.NdefMessage
import android.nfc.NdefRecord

/** Public navigation only: never a credential, pin, path, form or session. */
object NomadKeySharedAddress {
    private val address=Regex("[0-9a-f]{32}")
    private val uri=Regex("nomadnetwork://([0-9a-f]{32}):/page/index\\.mu")
    const val MAX_MESSAGE_BYTES=256

    fun validate(destination:String):String {
        require(address.matches(destination)) { "Invalid NomadNet destination" }
        return destination
    }

    fun message(destination:String)=NdefMessage(arrayOf(
        NdefRecord.createUri("nomadnetwork://${validate(destination)}:/page/index.mu"),
    ))

    fun read(message:NdefMessage?):String {
        require(message!=null && message.toByteArray().size<=MAX_MESSAGE_BYTES) { "No supported shared address on this tag" }
        val records=message.records
        require(records.size==1) { "Expected one shared site address" }
        val record=records.single()
        require(record.tnf==NdefRecord.TNF_WELL_KNOWN && record.type.contentEquals(NdefRecord.RTD_URI) && record.id.isEmpty()) { "Not a shared NomadNet address" }
        return uri.matchEntire(record.toUri()?.toString().orEmpty())?.groupValues?.get(1)
            ?: throw IllegalArgumentException("Only a NomadNet site landing address is supported")
    }

    fun blank(message:NdefMessage?):Boolean = message==null || message.records.all {
        it.tnf==NdefRecord.TNF_EMPTY && it.type.isEmpty() && it.id.isEmpty() && it.payload.isEmpty()
    }

    /** Idempotent existing address is fine; other content is never overwritten. */
    fun canWrite(existing:NdefMessage?,destination:String):Boolean =
        blank(existing) || runCatching { read(existing)==validate(destination) }.getOrDefault(false)
}
