package org.nomadkey.host;

import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.Test;
import static org.junit.Assert.*;
import android.content.Context;
import org.json.JSONObject;

/** Emulator checks only. No NFC, SIM, OTP coverage or real delivery claims. */
public class HostSmokeTest {
    @Test public void testSyntheticSmsProvider() throws Exception {
        Context context=InstrumentationRegistry.getInstrumentation().getTargetContext();
        org.junit.Assume.assumeTrue("Emulator READ_SMS grant required",context.checkSelfPermission(android.Manifest.permission.READ_SMS)==android.content.pm.PackageManager.PERMISSION_GRANTED);
        PhoneBridge bridge=new PhoneBridge(context);
        JSONObject first=new JSONObject(bridge.smsPage(0,0));
        assertFalse(first.has("error"));
        assertEquals(2,first.getJSONArray("messages").length());
        assertTrue(first.getBoolean("more"));
        assertTrue(first.getJSONArray("messages").getJSONObject(0).getString("body").startsWith("NOMADKEY-SYNTHETIC"));
        JSONObject second=new JSONObject(bridge.smsPage(2,first.getLong("anchor")));
        assertEquals(2,second.getJSONArray("messages").length());
        assertNotEquals(first.getJSONArray("messages").getJSONObject(0).getString("body"),second.getJSONArray("messages").getJSONObject(0).getString("body"));
        JSONObject events=new JSONObject(bridge.smsEvents(0));
        assertFalse(events.toString().contains("NOMADKEY-SYNTHETIC"));
        assertFalse(events.toString().contains("body"));
    }
    @Test public void testEmbeddedRuntimeAndDeniedInbox() throws Exception {
        Context context=InstrumentationRegistry.getInstrumentation().getTargetContext();
        PhoneBridge bridge=new PhoneBridge(context);
        assertTrue(new JSONObject(bridge.smsPage(-1,0)).has("error"));
        JSONObject sim=new JSONObject(bridge.simSnapshot());
        assertTrue(sim.has("observable"));
        String root=context.getCacheDir().getAbsolutePath()+"/isolated-smoke";
        String config="{\"mode\":\"pages\",\"name\":\"Isolated emulator test\",\"uplink\":\"127.0.0.1\",\"port\":39999}";
        JSONObject status=new JSONObject(HostService.module(context).callAttr("start",root,bridge,config).toString());
        assertEquals(32,status.getString("destination").length());
        assertEquals(128,status.getString("public_key").length());
        assertEquals(0,status.getInt("credentials"));
        assertEquals("Hosting Reticulum service",status.getString("connection"));
        assertEquals("[]",HostService.module(context).callAttr("credentials").toString());
        HostService.module(context).callAttr("shutdown");
    }
}
