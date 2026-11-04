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
        assertFalse(NomadKeyCeremony.stageResponse(input.generation,"assertion"))
        assertFalse(NomadKeyCeremony.tagRemoved(input.generation))
        assertNull(NomadKeyCeremony.takeResponse())
    }
    @Test fun newCeremonyInvalidatesOldAndResponseIsConsumedOnce() {
        NomadKeyCeremony.prepare("old", "old-pin")
        val old=NomadKeyCeremony.takeInput()!!
        NomadKeyCeremony.prepare("new", "new-pin")
        val current=NomadKeyCeremony.takeInput()!!
        assertFalse(NomadKeyCeremony.stageResponse(old.generation,"old-assertion"))
        assertTrue(NomadKeyCeremony.stageResponse(current.generation,"new-assertion"))
        assertNull(NomadKeyCeremony.takeResponse())
        assertTrue(NomadKeyCeremony.tagRemoved(current.generation))
        assertFalse(NomadKeyCeremony.tagRemoved(current.generation))
        assertEquals("new-assertion",NomadKeyCeremony.takeResponse())
        assertNull(NomadKeyCeremony.takeResponse())
        assertFalse(current.toString().contains("new-pin"))
    }

    @Test fun cancelWhileKeyIsPresentDiscardsStagedAssertion() {
        NomadKeyCeremony.prepare("request", "test-pin")
        val input=NomadKeyCeremony.takeInput()!!
        assertTrue(NomadKeyCeremony.stageResponse(input.generation,"assertion"))
        assertNull(NomadKeyCeremony.takeResponse())
        NomadKeyCeremony.clear() // pause, cancellation or removal timeout
        assertFalse(NomadKeyCeremony.tagRemoved(input.generation))
        assertNull(NomadKeyCeremony.takeResponse())
    }

    @Test fun oldRemovalCallbackCannotReleaseNewCeremony() {
        NomadKeyCeremony.prepare("old", "test-pin")
        val old=NomadKeyCeremony.takeInput()!!
        NomadKeyCeremony.stageResponse(old.generation,"old-assertion")
        NomadKeyCeremony.prepare("new", "test-pin")
        val current=NomadKeyCeremony.takeInput()!!
        assertTrue(NomadKeyCeremony.stageResponse(current.generation,"new-assertion"))
        assertFalse(NomadKeyCeremony.tagRemoved(old.generation))
        assertNull(NomadKeyCeremony.takeResponse())
        assertFalse(NomadKeyCeremony.stageResponse(current.generation,"replacement"))
        assertTrue(NomadKeyCeremony.tagRemoved(current.generation))
        assertEquals("new-assertion",NomadKeyCeremony.takeResponse())
    }
}
