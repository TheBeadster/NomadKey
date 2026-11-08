package org.nomadkey.host;

import android.Manifest;
import android.content.*;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import android.telephony.*;
import org.json.*;
import java.util.*;

/** Device-only providers. No body logging, copying to preferences, or notification use. */
public final class PhoneBridge {
    private final Context c;
    public PhoneBridge(Context context) {c=context.getApplicationContext();}
    private boolean granted(String permission) {return c.checkSelfPermission(permission)==PackageManager.PERMISSION_GRANTED;}
    private String error(String text) {try{return new JSONObject().put("error",text).toString();}catch(Exception e){return "{}";}}
    public String smsPage(int offset,long anchor) {
        if(!granted(Manifest.permission.READ_SMS))return error("SMS permission is unavailable. Grant it on the host if Android permits.");
        if(offset<0||offset>100000||anchor<0)return error("Invalid page position");
        try {
            if(anchor==0)anchor=latest();
            JSONArray messages=new JSONArray();boolean more=false;int skipped=0;int size=0;
            try(Cursor rows=c.getContentResolver().query(Uri.parse("content://sms/inbox"),new String[]{"_id","address","date","body"},"_id <= ?",new String[]{Long.toString(anchor)},"_id DESC")) {
                if(rows==null)return error("Android did not provide the SMS inbox");
                while(rows.moveToNext()) {
                    if(skipped++<offset)continue;
                    if(messages.length()==2){more=true;break;}
                    String body=rows.getString(3);if(body==null)body="";
                    size+=body.length();if(size>20000)return error("These messages exceed the safe page limit; read them locally. They have not been truncated.");
                    messages.put(new JSONObject().put("sender",rows.isNull(1)?"Unknown":rows.getString(1)).put("timestamp",rows.getLong(2)).put("body",body));
                }
            }
            return new JSONObject().put("messages",messages).put("anchor",anchor).put("more",more)
                .put("capability_note", "Android may hide sensitive/OTP messages. This list is only what the host OS exposes.").toString();
        } catch(Exception e){return error("SMS access failed or was restricted by Android");}
    }
    private long latest() {
        try(Cursor r=c.getContentResolver().query(Uri.parse("content://sms/inbox"),new String[]{"_id"},null,null,"_id DESC")) {
            return r!=null&&r.moveToFirst()?r.getLong(0):0;
        }
    }
    public String smsEvents(long last) {
        if(!granted(Manifest.permission.READ_SMS))return error("SMS permission unavailable");
        try {
            if(last<0)return new JSONObject().put("latest",latest()).put("events",new JSONArray()).toString();
            JSONArray events=new JSONArray();long newest=last;
            try(Cursor rows=c.getContentResolver().query(Uri.parse("content://sms/inbox"),new String[]{"_id","address","date"},"_id > ?",new String[]{Long.toString(last)},"_id ASC")) {
                if(rows==null)return error("Inbox unavailable");
                while(rows.moveToNext()&&events.length()<100) {
                    newest=rows.getLong(0);
                    events.put(new JSONObject().put("sender",rows.isNull(1)?"Unknown":rows.getString(1)).put("timestamp",rows.getLong(2)));
                }
            }
            return new JSONObject().put("latest",newest).put("events",events).toString();
        } catch(Exception e){return error("SMS observation restricted");}
    }
    public String simSnapshot() {
        JSONObject result=new JSONObject();JSONArray sims=new JSONArray();
        try {
            boolean observable=c.checkSelfPermission(Manifest.permission.READ_PHONE_STATE)==PackageManager.PERMISSION_GRANTED;
            result.put("observable",observable).put("sims",sims).put("in_service",false)
                .put("airplane",Settings.Global.getInt(c.getContentResolver(),Settings.Global.AIRPLANE_MODE_ON,0)!=0)
                .put("identity_assurance","Subscription metadata only; cannot confirm carrier-side SIM swaps");
            if(!observable)return result.toString();
            List<SubscriptionInfo> list=c.getSystemService(SubscriptionManager.class).getActiveSubscriptionInfoList();
            boolean all=true;
            if(list!=null){
                list.sort(Comparator.comparingInt(SubscriptionInfo::getSimSlotIndex));
                for(SubscriptionInfo info:list){
                    sims.put(new JSONObject().put("slot",info.getSimSlotIndex()).put("subscription",info.getSubscriptionId()).put("carrier",String.valueOf(info.getCarrierName())));
                    TelephonyManager tm=c.getSystemService(TelephonyManager.class).createForSubscriptionId(info.getSubscriptionId());
                    if(c.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)!=PackageManager.PERMISSION_GRANTED)throw new SecurityException();
                    ServiceState s=Build.VERSION.SDK_INT>=33 ? tm.getServiceState(TelephonyManager.INCLUDE_LOCATION_DATA_NONE) : legacyServiceState(tm);
                    all &= s!=null && s.getState()==ServiceState.STATE_IN_SERVICE;
                }
            }
            result.put("in_service",sims.length()>0 && all);
        }catch(SecurityException e){try{result.put("observable",false);}catch(Exception ignored){}}
        catch(Exception e){try{result.put("observable",false);}catch(Exception ignored){}}
        return result.toString();
    }
    private ServiceState legacyServiceState(TelephonyManager tm) {
        // Older Android may additionally demand location; no location collection or
        // permission bypass. Report monitoring unavailable if the OS rejects it.
        if(c.checkSelfPermission(Manifest.permission.READ_PHONE_STATE)!=PackageManager.PERMISSION_GRANTED || c.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)!=PackageManager.PERMISSION_GRANTED)throw new SecurityException();
        return tm.getServiceState();
    }
}
