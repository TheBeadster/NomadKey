package network.columba.app.viewmodel

import network.columba.app.rns.api.NomadKeyCeremony
import org.junit.After
import org.junit.Assert.*
import org.junit.Test

class NomadKeyCeremonyTest {
    @After fun clear() { NomadKeyCeremony.clear() }
    @Test fun cancelledCeremonyCannotReturnLateAssertion() {
        NomadKeyCeremony.prepare("request", "test-pin")
        val input=NomadKeyCeremony.takeInput()!!
        assertNull(NomadKeyCeremony.takeInput())
        NomadKeyCeremony.clear()
        assertFalse(NomadKeyCeremony.complete(input.generation,"assertion"))
        assertNull(NomadKeyCeremony.takeResponse())
    }
    @Test fun newCeremonyInvalidatesOldAndResponseIsConsumedOnce() {
        NomadKeyCeremony.prepare("old", "old-pin")
        val old=NomadKeyCeremony.takeInput()!!
        NomadKeyCeremony.prepare("new", "new-pin")
        val current=NomadKeyCeremony.takeInput()!!
        assertFalse(NomadKeyCeremony.complete(old.generation,"old-assertion"))
        assertTrue(NomadKeyCeremony.complete(current.generation,"new-assertion"))
        assertEquals("new-assertion",NomadKeyCeremony.takeResponse())
        assertNull(NomadKeyCeremony.takeResponse())
        assertFalse(current.toString().contains("new-pin"))
    }
}
