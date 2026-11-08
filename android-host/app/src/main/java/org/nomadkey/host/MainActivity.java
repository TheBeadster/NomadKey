package org.nomadkey.host;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.os.*;
import android.text.InputType;
import android.view.*;
import android.widget.*;
import org.json.*;

public class MainActivity extends Activity {
    private TextView status;
    private EditText name,uplink,port;
    private Switch sms;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private JSONObject pending;
    private final Runnable refresh=new Runnable(){public void run(){status.setText(statusText());handler.postDelayed(this,2000);}};
    private String statusText(){
        try{JSONObject s=new JSONObject(HostService.state);return s.getString("connection")+"\n\nFull site destination:\n"+s.getString("destination")+"\n\nEnrolled keys: "+s.getInt("credentials")+"\nAlert destinations: "+s.getInt("subscribers")+(s.optString("mode").equals("sms")?"\n\n"+s.optString("sim")+"\n"+s.optString("sms"):"")+"\nDropped alerts: "+s.optInt("dropped_alerts");}catch(Exception e){return HostService.state;}
    }
    public void onCreate(Bundle saved) {
        super.onCreate(saved);getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);
        ScrollView scroll=new ScrollView(this);LinearLayout layout=new LinearLayout(this);layout.setOrientation(LinearLayout.VERTICAL);layout.setPadding(24,48,24,48);scroll.addView(layout);setContentView(scroll);
        label(layout,"NomadKey Host DEV",26);
        label(layout,"A private page or SMS inbox, unlocked with your security key. Development build: device testing required.",16);
        name=field(layout,"Public site name","NomadKey Host");uplink=field(layout,"Reticulum TCP host","mh.beady.com");port=field(layout,"TCP port","444");port.setInputType(InputType.TYPE_CLASS_NUMBER);
        sms=new Switch(this);sms.setText("SMS relay (off = private page only)");layout.addView(sms);
        try{JSONObject config=new JSONObject(getSharedPreferences("host",0).getString("config","{}"));name.setText(config.optString("name","NomadKey Host"));uplink.setText(config.optString("uplink","mh.beady.com"));port.setText(""+config.optInt("port",444));sms.setChecked(config.optString("mode").equals("sms"));}catch(Exception ignored){}
        button(layout,"Start host",()->startHost());
        button(layout,"Stop host and close app",()->new AlertDialog.Builder(this).setMessage("Stop serving and revoke all current sessions? The app closes to reset Reticulum safely.").setPositiveButton("Stop",(d,w)->{stopService(new Intent(this,HostService.class));finish();}).setNegativeButton("Cancel",null).show());
        status=label(layout,HostService.state,15);status.setTextIsSelectable(true);
        label(layout,"Local administration",22);
        button(layout,"Enrol owner / approved reader key",()->act(json("action","enroll")));
        button(layout,"Approve adding a reader key",()->act(json("action","authorize_enroll")));
        button(layout,"Approve adding a backup owner key",()->act(ownerOperation("authorize_enroll")));
        button(layout,"Enrol approved backup owner key",()->act(ownerOperation("enroll")));
        button(layout,"Review and trust current SIM",()->reviewSim());
        button(layout,"Save this site on a FIDO2 key",()->act(json("action","bookmark")));
        button(layout,"Edit protected page",()->editPage());
        button(layout,"Remove enrolled credential",()->removeCredential());
        label(layout,"First enrolment creates the owner. Adding a reader requires an owner-key approval, then the new key within 60 seconds. Readers can browse and register their own alert destination. Only the owner can change this host.",15);
        label(layout,"SMS mode needs Android SMS and phone permissions. Some phones restrict these permissions or hide OTP messages. The app does not become your default SMS app. SIM monitoring detects visible changes and service loss, not a proven SIM swap. Keep Wi-Fi or another mesh route available if you want alerts when the SIM fails.",15);
        label(layout,"Android also gates service-state checks behind approximate-location permission. No coordinates are stored or sent. If background restrictions block that check, monitoring reports unavailable.",15);
        label(layout,"This version starts only when you press Start. It does not auto-start after reboot. Keep the hosting notification active; Android/OEM battery restrictions can stop background hosting.",15);
    }
    private TextView label(LinearLayout parent,String text,int size){TextView v=new TextView(this);v.setText(text);v.setTextSize(size);v.setPadding(0,12,0,12);parent.addView(v);return v;}
    private EditText field(LinearLayout parent,String hint,String value){EditText e=new EditText(this);e.setHint(hint);e.setText(value);e.setSingleLine(true);parent.addView(e);return e;}
    private void button(LinearLayout p,String text,Runnable run){Button b=new Button(this);b.setText(text);p.addView(b);b.setOnClickListener(v->run.run());}
    private JSONObject json(String key,String value){try{return new JSONObject().put(key,value);}catch(Exception e){throw new IllegalStateException();}}
    private JSONObject ownerOperation(String action){try{return json("action",action).put("permissions",new JSONArray().put("pages:read").put("notifications:manage").put("admin"));}catch(Exception e){throw new IllegalStateException();}}
    private void message(String text){new AlertDialog.Builder(this).setMessage(text).setPositiveButton("OK",null).show();}
    private void startHost(){
        if(HostService.running){message("Already started. Stop and reopen to change mode or connection settings.");return;}
        try {
            int number=Integer.parseInt(port.getText().toString());String host=uplink.getText().toString().trim();String title=name.getText().toString().trim();
            if(number<1||number>65535||!host.matches("[A-Za-z0-9.-]{1,253}")||title.isEmpty()||title.length()>48)throw new IllegalArgumentException();
            JSONObject config=new JSONObject().put("name",title).put("mode",sms.isChecked()?"sms":"pages").put("uplink",host).put("port",number).put("lifetime",300);
            getSharedPreferences("host",0).edit().putString("config",config.toString()).apply();
            java.util.ArrayList<String> permissions=new java.util.ArrayList<>();
            if(sms.isChecked()){permissions.add(Manifest.permission.READ_SMS);permissions.add(Manifest.permission.READ_PHONE_STATE);permissions.add(Manifest.permission.ACCESS_COARSE_LOCATION);}
            if(Build.VERSION.SDK_INT>=33)permissions.add(Manifest.permission.POST_NOTIFICATIONS);
            permissions.removeIf(p->checkSelfPermission(p)==android.content.pm.PackageManager.PERMISSION_GRANTED);
            if(!permissions.isEmpty())requestPermissions(permissions.toArray(new String[0]),10);else launch();
        }catch(Exception e){message("Enter a site name (1-48 characters), TCP hostname and port 1-65535.");}
    }
    private void launch(){startForegroundService(new Intent(this,HostService.class));}
    public void onRequestPermissionsResult(int request,String[] p,int[] results){super.onRequestPermissionsResult(request,p,results);if(request==10)launch();}
    private void act(JSONObject operation){
        if(!HostService.running){message("Start the host first.");return;}
        KeyguardManager km=getSystemService(KeyguardManager.class);
        if(!km.isDeviceSecure()){message("Set a secure screen lock first. Initial owner enrolment requires trusted local administration.");return;}
        Intent confirm=km.createConfirmDeviceCredentialIntent("NomadKey local administration","Unlock this phone to continue. Existing host changes also require its owner key.");
        if(confirm==null){message("Device unlock is unavailable.");return;}
        pending=operation;startActivityForResult(confirm,20);
    }
    protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(request==20){JSONObject op=pending;pending=null;if(result==RESULT_OK&&op!=null)startActivity(new Intent(this,KeyActivity.class).putExtra("operation",op.toString()));}}
    private void reviewSim(){
        if(!HostService.running){message("Start the host first.");return;}
        String raw=new PhoneBridge(this).simSnapshot();
        new AlertDialog.Builder(this).setTitle("Trust this SIM observation?").setMessage(raw+"\n\nThis is subscription metadata, not proof of the SIM's unique identity. Changes need local review.")
            .setPositiveButton("Trust with owner key",(d,w)->{try{act(json("action","trust_sim").put("snapshot",new JSONObject(raw)));}catch(Exception ignored){}}).setNegativeButton("Cancel",null).show();
    }
    private void editPage(){EditText page=new EditText(this);page.setHint("Micron page text");page.setMinLines(6);page.setMaxLines(16);page.setText(">Private site\nWelcome to your secure NomadNet host.\n");new AlertDialog.Builder(this).setTitle("Replace private page").setView(page).setPositiveButton("Save with owner key",(d,w)->{try{act(json("action","save_page").put("page",page.getText().toString()));}catch(Exception ignored){}}).setNegativeButton("Cancel",null).show();}
    private void removeCredential(){
        if(!HostService.running){message("Start the host first.");return;}
        new Thread(()->{try{JSONArray rows=new JSONArray(HostService.module(this).callAttr("credentials").toString());String[] labels=new String[rows.length()];for(int i=0;i<labels.length;i++)labels[i]=rows.getJSONObject(i).getString("id")+"\n"+rows.getJSONObject(i).getJSONArray("permissions");runOnUiThread(()->new AlertDialog.Builder(this).setTitle("Revoke credential and sessions").setItems(labels,(d,w)->{try{act(json("action","remove").put("credential",rows.getJSONObject(w).getString("id")));}catch(Exception ignored){}}).setNegativeButton("Cancel",null).show());}catch(Exception e){runOnUiThread(()->message("Credential list unavailable"));}}).start();
    }
    protected void onResume(){super.onResume();handler.post(refresh);}
    protected void onPause(){handler.removeCallbacks(refresh);super.onPause();}
}
